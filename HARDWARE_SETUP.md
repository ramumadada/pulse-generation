# Hardware Setup

## Incremental Amplitude Pulse Mode

This mode creates real analog amplitude steps by combining Arduino gate timing with SEELab PV1 voltage control.

## Connections

```text
Arduino D9
-> NMOS Gate

SEELab PV1
-> NMOS Drain

NMOS Source
-> Output Pulse
-> Load / Memristor

Load Return
-> Ground

SEELab A1
-> Output Pulse Observation

SEELab A2
-> Current / Load Observation
```

## Recommended Safety

- Use a gate resistor between Arduino D9 and MOSFET gate.
- Use a load/sense resistor appropriate for the current range.
- Keep PV1 from 0 V to 5 V.
- Keep Arduino pin current below safe digital input/output limits.
- Do not drive a power load directly from Arduino.
- Share ground between Arduino, SEELab, and the external circuit.

## Operating Principle

Python sets PV1 to the next amplitude step.

Arduino D9 fires a hardware-timed gate pulse.

The MOSFET switches the PV1 voltage into the load.

SEELab A1/A2 capture the resulting waveform.
