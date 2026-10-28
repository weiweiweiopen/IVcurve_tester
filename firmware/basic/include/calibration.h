#pragma once
#include <math.h>
// Calibration entry point. Defaults are NOT measured. Record instrument,
// date, DUT range and temperature in calibration-record.md before changing.
constexpr float adcGainCorrection = 1.0f;
constexpr float adcOffsetVolts = 0.0f;
constexpr bool voltageCalibrated = false;
// Measured TOTAL path resistance including switch Ron, per channel.
// NAN means unknown: never substitute 2 or 64 ohms as a measured Ron.
constexpr float measuredPathOhms[16] = {NAN,NAN,NAN,NAN,NAN,NAN,NAN,NAN,NAN,NAN,NAN,NAN,NAN,NAN,NAN,NAN};
constexpr float nominalLoadOhms[16] = {1000000,20000,8200,4300,2200,1000,750,470,330,220,150,100,75,49.9,30.1,20};
// Diagnostic software stop only, NOT hardware protection or a DUT rating.
constexpr float nominalAbortMilliAmps = 5.0f;
constexpr float adcAbortVolts = 3.0f;
