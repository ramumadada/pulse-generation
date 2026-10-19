// PGEE Arduino UNO Pulse Engine
//
// Arduino performs real-time pulse/PWM/burst timing.
// Python sends configuration commands over Serial.
//
// Commands:
//   PING TOKEN=PGEE
//   STATUS
//   CONFIG_PULSE PIN=9 HIGH_US=1000 LOW_US=1000 COUNT=10 IDLE=0
//   START_PULSE
//   STOP_PULSE
//   CONFIG_BURST PIN=9 HIGH_US=1000 LOW_US=1000 PULSES=10 PACKETS=5 DELAY_MS=100
//   START_BURST
//   STOP_BURST
//   CONFIG_FAST_BURST FREQ_HZ=2000000 DUTY=33 CYCLES=100 OFF_US=500 BURSTS=0
//   START_FAST_BURST
//   STOP_FAST_BURST
//   CONFIG_PWM PIN=9 FREQ_HZ=1000 DUTY=50 DURATION_MS=0
//   START_PWM
//   STOP_PWM

struct PulseConfig {
  byte pin;
  unsigned long highUs;
  unsigned long lowUs;
  unsigned long count;
  byte idleState;
};

struct BurstConfig {
  byte pin;
  unsigned long highUs;
  unsigned long lowUs;
  unsigned long pulses;
  unsigned long packets;
  unsigned long delayMs;
};

struct PwmConfig {
  byte pin;
  float frequencyHz;
  float dutyPercent;
  unsigned long durationMs;
};

struct FastBurstConfig {
  unsigned long frequencyHz;
  float dutyPercent;
  unsigned long cyclesPerBurst;
  unsigned long offUs;
  unsigned long burstCount;
};

PulseConfig pulseConfig = {9, 1000UL, 1000UL, 10UL, LOW};
BurstConfig burstConfig = {9, 1000UL, 1000UL, 10UL, 1UL, 100UL};
PwmConfig pwmConfig = {9, 1000.0, 50.0, 0UL};
FastBurstConfig fastBurstConfig = {2000000UL, 33.0, 100UL, 500UL, 0UL};

// WHY CHANGED: Arduino String causes heap fragmentation on UNO (2 KB SRAM).
// Repeated concatenation in long experiment sessions leads to crashes or
// garbled commands. A fixed-size char buffer avoids any heap allocation.
char cmdBuf[128];
uint8_t cmdLen = 0;

bool pulseActive = false;
bool pulseHigh = false;
unsigned long pulseRemaining = 0;
unsigned long pulseNextUs = 0;

bool burstActive = false;
bool burstHigh = false;
bool burstWaiting = false;
unsigned long burstPacketsRemaining = 0;
unsigned long burstPulsesRemaining = 0;
unsigned long burstNextUs = 0;
unsigned long burstWaitUntilMs = 0;

bool pwmActive = false;
bool pwmHigh = false;
unsigned long pwmPeriodUs = 1000;
unsigned long pwmHighUs = 500;
unsigned long pwmNextUs = 0;
unsigned long pwmStartMs = 0;

bool fastBurstActive = false;
bool fastBurstOutputOn = false;
unsigned long fastBurstBurstsRemaining = 0;
unsigned long fastBurstNextUs = 0;
unsigned long fastBurstOnUs = 50;

void setup() {
  Serial.begin(115200);
  cmdBuf[0] = '\0';
  cmdLen = 0;
  pinMode(pulseConfig.pin, OUTPUT);
  digitalWrite(pulseConfig.pin, pulseConfig.idleState);
  Serial.println(F("FW PGEE_ARDUINO_PULSE_ENGINE 1.0"));
}

void loop() {
  readSerial();
  updatePulse();
  updateBurst();
  updatePwm();
  updateFastBurst();
}

void readSerial() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();

    if (c == '\n' || c == '\r') {
      if (cmdLen > 0) {
        cmdBuf[cmdLen] = '\0';
        handleCommand(String(cmdBuf));  // String created once per command, not per char
        cmdLen = 0;
        cmdBuf[0] = '\0';
      }
      continue;
    }

    if (cmdLen < 120) {
      cmdBuf[cmdLen++] = c;
    } else {
      cmdLen = 0;
      cmdBuf[0] = '\0';
      Serial.println(F("ERR LINE_TOO_LONG"));
    }
  }
}

void handleCommand(String line) {
  line.trim();
  line.toUpperCase();

  if (line.startsWith(F("PING"))) {
    String token = getValue(line, "TOKEN", "");
    Serial.print(F("ACK PONG TOKEN="));
    Serial.println(token);
    return;
  }

  if (line.startsWith(F("STATUS"))) {
    Serial.print(F("ACK STATUS PULSE="));
    Serial.print(pulseActive ? F("ON") : F("OFF"));
    Serial.print(F(" BURST="));
    Serial.print(burstActive ? F("ON") : F("OFF"));
    Serial.print(F(" PWM="));
    Serial.print(pwmActive ? F("ON") : F("OFF"));
    Serial.print(F(" FAST="));
    Serial.println(fastBurstActive ? F("ON") : F("OFF"));
    return;
  }

  if (line.startsWith(F("CONFIG_PULSE"))) {
    pulseConfig.pin = constrain(getLong(line, "PIN", pulseConfig.pin), 2, 13);
    pulseConfig.highUs = max(1UL, getUnsigned(line, "HIGH_US", pulseConfig.highUs));
    pulseConfig.lowUs = max(1UL, getUnsigned(line, "LOW_US", pulseConfig.lowUs));
    pulseConfig.count = max(1UL, getUnsigned(line, "COUNT", pulseConfig.count));
    pulseConfig.idleState = getLong(line, "IDLE", pulseConfig.idleState) == 0 ? LOW : HIGH;
    pinMode(pulseConfig.pin, OUTPUT);
    digitalWrite(pulseConfig.pin, pulseConfig.idleState);
    Serial.println(F("ACK CONFIG_PULSE"));
    return;
  }

  if (line.startsWith(F("START_PULSE"))) {
    startPulse();
    Serial.println(F("ACK START_PULSE"));
    return;
  }

  if (line.startsWith(F("STOP_PULSE"))) {
    stopPulse(true);
    return;
  }

  if (line.startsWith(F("CONFIG_BURST"))) {
    burstConfig.pin = constrain(getLong(line, "PIN", burstConfig.pin), 2, 13);
    burstConfig.highUs = max(1UL, getUnsigned(line, "HIGH_US", burstConfig.highUs));
    burstConfig.lowUs = max(1UL, getUnsigned(line, "LOW_US", burstConfig.lowUs));
    burstConfig.pulses = max(1UL, getUnsigned(line, "PULSES", burstConfig.pulses));
    burstConfig.packets = max(1UL, getUnsigned(line, "PACKETS", burstConfig.packets));
    burstConfig.delayMs = getUnsigned(line, "DELAY_MS", burstConfig.delayMs);
    pinMode(burstConfig.pin, OUTPUT);
    digitalWrite(burstConfig.pin, LOW);
    Serial.println(F("ACK CONFIG_BURST"));
    return;
  }

  if (line.startsWith(F("START_BURST"))) {
    startBurst();
    Serial.println(F("ACK START_BURST"));
    return;
  }

  if (line.startsWith(F("STOP_BURST"))) {
    stopBurst(true);
    return;
  }

  if (line.startsWith(F("CONFIG_FAST_BURST"))) {
    fastBurstConfig.frequencyHz = constrain(
      getUnsigned(line, "FREQ_HZ", fastBurstConfig.frequencyHz),
      1UL,
      2000000UL
    );
    fastBurstConfig.dutyPercent = constrain(
      getFloat(line, "DUTY", fastBurstConfig.dutyPercent),
      1.0,
      99.0
    );
    fastBurstConfig.cyclesPerBurst = max(
      1UL,
      getUnsigned(line, "CYCLES", fastBurstConfig.cyclesPerBurst)
    );
    fastBurstConfig.offUs = max(
      1UL,
      getUnsigned(line, "OFF_US", fastBurstConfig.offUs)
    );
    fastBurstConfig.burstCount = getUnsigned(
      line,
      "BURSTS",
      fastBurstConfig.burstCount
    );
    configureFastBurstTimer();
    Serial.println(F("ACK CONFIG_FAST_BURST"));
    return;
  }

  if (line.startsWith(F("START_FAST_BURST"))) {
    startFastBurst();
    Serial.println(F("ACK START_FAST_BURST"));
    return;
  }

  if (line.startsWith(F("STOP_FAST_BURST"))) {
    stopFastBurst(true);
    return;
  }

  if (line.startsWith(F("CONFIG_PWM"))) {
    pwmConfig.pin = constrain(getLong(line, "PIN", pwmConfig.pin), 2, 13);
    pwmConfig.frequencyHz = max(0.1, getFloat(line, "FREQ_HZ", pwmConfig.frequencyHz));
    pwmConfig.dutyPercent = constrain(getFloat(line, "DUTY", pwmConfig.dutyPercent), 0.0, 100.0);
    pwmConfig.durationMs = getUnsigned(line, "DURATION_MS", pwmConfig.durationMs);
    pinMode(pwmConfig.pin, OUTPUT);
    digitalWrite(pwmConfig.pin, LOW);
    Serial.println(F("ACK CONFIG_PWM"));
    return;
  }

  if (line.startsWith(F("START_PWM"))) {
    startPwm();
    Serial.println(F("ACK START_PWM"));
    return;
  }

  if (line.startsWith(F("STOP_PWM"))) {
    stopPwm(true);
    return;
  }

  Serial.println(F("ERR UNKNOWN_COMMAND"));
}

void startPulse() {
  stopBurst(false);
  stopPwm(false);
  stopFastBurst(false);
  pulseRemaining = pulseConfig.count;
  pulseHigh = true;
  pulseActive = true;
  digitalWrite(pulseConfig.pin, HIGH);
  pulseNextUs = micros() + pulseConfig.highUs;
}

void updatePulse() {
  if (!pulseActive || (long)(micros() - pulseNextUs) < 0) {
    return;
  }

  unsigned long nowUs = micros();

  if (pulseHigh) {
    pulseHigh = false;
    digitalWrite(pulseConfig.pin, LOW);
    pulseNextUs = nowUs + pulseConfig.lowUs;
    return;
  }

  if (pulseRemaining > 0) {
    pulseRemaining--;
  }

  if (pulseRemaining == 0) {
    stopPulse(false);
    Serial.println(F("ACK DONE_PULSE"));
    return;
  }

  pulseHigh = true;
  digitalWrite(pulseConfig.pin, HIGH);
  pulseNextUs = nowUs + pulseConfig.highUs;
}

void stopPulse(bool ack) {
  pulseActive = false;
  pulseHigh = false;
  digitalWrite(pulseConfig.pin, pulseConfig.idleState);
  if (ack) {
    Serial.println(F("ACK STOP_PULSE"));
  }
}

void startBurst() {
  stopPulse(false);
  stopPwm(false);
  stopFastBurst(false);
  burstPacketsRemaining = burstConfig.packets;
  burstActive = true;
  burstWaiting = false;
  beginBurstPacket();
}

void beginBurstPacket() {
  burstPulsesRemaining = burstConfig.pulses;
  burstHigh = true;
  digitalWrite(burstConfig.pin, HIGH);
  burstNextUs = micros() + burstConfig.highUs;
}

void updateBurst() {
  if (!burstActive) {
    return;
  }

  if (burstWaiting) {
    if ((long)(millis() - burstWaitUntilMs) >= 0) {
      burstWaiting = false;
      beginBurstPacket();
    }
    return;
  }

  if ((long)(micros() - burstNextUs) < 0) {
    return;
  }

  unsigned long nowUs = micros();

  if (burstHigh) {
    burstHigh = false;
    digitalWrite(burstConfig.pin, LOW);
    burstNextUs = nowUs + burstConfig.lowUs;
    return;
  }

  if (burstPulsesRemaining > 0) {
    burstPulsesRemaining--;
  }

  if (burstPulsesRemaining > 0) {
    burstHigh = true;
    digitalWrite(burstConfig.pin, HIGH);
    burstNextUs = nowUs + burstConfig.highUs;
    return;
  }

  if (burstPacketsRemaining > 0) {
    burstPacketsRemaining--;
  }

  if (burstPacketsRemaining == 0) {
    stopBurst(false);
    Serial.println(F("ACK DONE_BURST"));
    return;
  }

  burstWaiting = true;
  burstWaitUntilMs = millis() + burstConfig.delayMs;
}

void stopBurst(bool ack) {
  burstActive = false;
  burstHigh = false;
  burstWaiting = false;
  digitalWrite(burstConfig.pin, LOW);
  if (ack) {
    Serial.println(F("ACK STOP_BURST"));
  }
}

void startPwm() {
  stopPulse(false);
  stopBurst(false);
  stopFastBurst(false);
  pwmPeriodUs = max(2UL, (unsigned long)(1000000.0 / pwmConfig.frequencyHz));
  pwmHighUs = (unsigned long)(pwmPeriodUs * pwmConfig.dutyPercent / 100.0);
  pwmStartMs = millis();
  pwmActive = true;
  pwmHigh = pwmHighUs > 0;
  digitalWrite(pwmConfig.pin, pwmHigh ? HIGH : LOW);
  pwmNextUs = micros() + (pwmHigh ? pwmHighUs : pwmPeriodUs);
}

void updatePwm() {
  if (!pwmActive) {
    return;
  }

  if (pwmConfig.durationMs > 0 && millis() - pwmStartMs >= pwmConfig.durationMs) {
    stopPwm(false);
    Serial.println(F("ACK DONE_PWM"));
    return;
  }

  if (pwmHighUs == 0 || pwmHighUs >= pwmPeriodUs) {
    return;
  }

  if ((long)(micros() - pwmNextUs) < 0) {
    return;
  }

  unsigned long nowUs = micros();
  pwmHigh = !pwmHigh;
  digitalWrite(pwmConfig.pin, pwmHigh ? HIGH : LOW);
  pwmNextUs = nowUs + (pwmHigh ? pwmHighUs : (pwmPeriodUs - pwmHighUs));
}

void stopPwm(bool ack) {
  pwmActive = false;
  pwmHigh = false;
  digitalWrite(pwmConfig.pin, LOW);
  if (ack) {
    Serial.println(F("ACK STOP_PWM"));
  }
}

void configureFastBurstTimer() {
  DDRB |= (1 << DDB1);

  unsigned long prescaler = 1UL;
  byte clockSelectBits = (1 << CS10);
  unsigned long topValue = (16000000UL / fastBurstConfig.frequencyHz) - 1UL;

  if (topValue > 65535UL) {
    prescaler = 8UL;
    clockSelectBits = (1 << CS11);
    topValue = (16000000UL / (prescaler * fastBurstConfig.frequencyHz)) - 1UL;
  }

  if (topValue > 65535UL) {
    prescaler = 64UL;
    clockSelectBits = (1 << CS11) | (1 << CS10);
    topValue = (16000000UL / (prescaler * fastBurstConfig.frequencyHz)) - 1UL;
  }

  if (topValue > 65535UL) {
    prescaler = 256UL;
    clockSelectBits = (1 << CS12);
    topValue = (16000000UL / (prescaler * fastBurstConfig.frequencyHz)) - 1UL;
  }

  if (topValue > 65535UL) {
    prescaler = 1024UL;
    clockSelectBits = (1 << CS12) | (1 << CS10);
    topValue = (16000000UL / (prescaler * fastBurstConfig.frequencyHz)) - 1UL;
  }

  topValue = constrain(topValue, 1UL, 65535UL);

  ICR1 = (unsigned int)topValue;

  unsigned int compareValue = (unsigned int)((fastBurstConfig.dutyPercent / 100.0) * ICR1);
  if (compareValue > ICR1) {
    compareValue = ICR1;
  }
  OCR1A = compareValue;

  TCCR1A = (1 << WGM11);
  TCCR1B = (1 << WGM13) | (1 << WGM12) | clockSelectBits;

  fastBurstOnUs = max(
    1UL,
    (unsigned long)((1000000.0 * fastBurstConfig.cyclesPerBurst) / fastBurstConfig.frequencyHz)
  );

  TCCR1A &= ~(1 << COM1A1);
  PORTB &= ~(1 << PORTB1);
}

void startFastBurst() {
  stopPulse(false);
  stopBurst(false);
  stopPwm(false);
  configureFastBurstTimer();

  fastBurstBurstsRemaining = fastBurstConfig.burstCount;
  fastBurstActive = true;
  beginFastBurstOn();
}

void beginFastBurstOn() {
  fastBurstOutputOn = true;
  TCCR1A |= (1 << COM1A1);
  fastBurstNextUs = micros() + fastBurstOnUs;
}

void updateFastBurst() {
  if (!fastBurstActive) {
    return;
  }

  if ((long)(micros() - fastBurstNextUs) < 0) {
    return;
  }

  unsigned long nowUs = micros();

  if (fastBurstOutputOn) {
    TCCR1A &= ~(1 << COM1A1);
    PORTB &= ~(1 << PORTB1);
    fastBurstOutputOn = false;

    if (fastBurstConfig.burstCount > 0UL) {
      if (fastBurstBurstsRemaining > 0UL) {
        fastBurstBurstsRemaining--;
      }

      if (fastBurstBurstsRemaining == 0UL) {
        stopFastBurst(false);
        Serial.println(F("ACK DONE_FAST_BURST"));
        return;
      }
    }

    fastBurstNextUs = nowUs + fastBurstConfig.offUs;
    return;
  }

  beginFastBurstOn();
}

void stopFastBurst(bool ack) {
  fastBurstActive = false;
  fastBurstOutputOn = false;
  TCCR1A &= ~(1 << COM1A1);
  PORTB &= ~(1 << PORTB1);
  if (ack) {
    Serial.println(F("ACK STOP_FAST_BURST"));
  }
}

String getValue(String line, String key, String fallback) {
  String token = key + "=";
  int start = line.indexOf(token);
  if (start < 0) {
    return fallback;
  }

  start += token.length();
  int end = line.indexOf(' ', start);
  if (end < 0) {
    end = line.length();
  }

  return line.substring(start, end);
}

long getLong(String line, String key, long fallback) {
  return getValue(line, key, String(fallback)).toInt();
}

unsigned long getUnsigned(String line, String key, unsigned long fallback) {
  return (unsigned long)getValue(line, key, String(fallback)).toInt();
}

float getFloat(String line, String key, float fallback) {
  return getValue(line, key, String(fallback, 3)).toFloat();
}
