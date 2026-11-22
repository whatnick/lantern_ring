#ifndef RGBW_CONFIG_H
#define RGBW_CONFIG_H

/* 0: fixed colour; 1: PB3/JP1 selects open or bridged colour at startup. */
#ifndef RGBW_MODE
#define RGBW_MODE 0
#endif

#ifndef RGBW_FIXED_R
#define RGBW_FIXED_R 0
#endif
#ifndef RGBW_FIXED_G
#define RGBW_FIXED_G 96
#endif
#ifndef RGBW_FIXED_B
#define RGBW_FIXED_B 0
#endif
#ifndef RGBW_FIXED_W
#define RGBW_FIXED_W 0
#endif

#ifndef RGBW_OPEN_R
#define RGBW_OPEN_R 0
#endif
#ifndef RGBW_OPEN_G
#define RGBW_OPEN_G 96
#endif
#ifndef RGBW_OPEN_B
#define RGBW_OPEN_B 0
#endif
#ifndef RGBW_OPEN_W
#define RGBW_OPEN_W 0
#endif

#ifndef RGBW_BRIDGED_R
#define RGBW_BRIDGED_R 96
#endif
#ifndef RGBW_BRIDGED_G
#define RGBW_BRIDGED_G 0
#endif
#ifndef RGBW_BRIDGED_B
#define RGBW_BRIDGED_B 0
#endif
#ifndef RGBW_BRIDGED_W
#define RGBW_BRIDGED_W 0
#endif

#if RGBW_MODE != 0 && RGBW_MODE != 1
#error "RGBW_MODE must be 0 (fixed) or 1 (JP1 selector)"
#endif

#define RGBW_VALID(v) ((v) >= 0 && (v) <= 255)
#if !RGBW_VALID(RGBW_FIXED_R) || !RGBW_VALID(RGBW_FIXED_G) || \
    !RGBW_VALID(RGBW_FIXED_B) || !RGBW_VALID(RGBW_FIXED_W) || \
    !RGBW_VALID(RGBW_OPEN_R) || !RGBW_VALID(RGBW_OPEN_G) || \
    !RGBW_VALID(RGBW_OPEN_B) || !RGBW_VALID(RGBW_OPEN_W) || \
    !RGBW_VALID(RGBW_BRIDGED_R) || !RGBW_VALID(RGBW_BRIDGED_G) || \
    !RGBW_VALID(RGBW_BRIDGED_B) || !RGBW_VALID(RGBW_BRIDGED_W)
#error "RGBW channel values must be in the range 0..255"
#endif

#endif
