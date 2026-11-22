#include <cassert>
#include <cstdint>

uint8_t PORTB, DDRB, PINB, TCCR0A, TCCR0B, TCCR1, GTCCR, TIMSK;
uint8_t TCNT0, TCNT1, OCR0A, OCR0B, OCR1A, OCR1B, OCR1C, TIFR;

#define main firmware_main
#include "../rgbw.c"
#undef main

static void reset_registers()
{
    PORTB = DDRB = PINB = TCCR0A = TCCR0B = TCCR1 = GTCCR = TIMSK = 0;
    TCNT0 = TCNT1 = OCR0A = OCR0B = OCR1A = OCR1B = OCR1C = TIFR = 0;
}

int main()
{
    reset_registers();
    PORTB = _BV(PB3);
    DDRB = _BV(PB3);
    init_pins();
    assert(!(DDRB & _BV(PB3)) && !(PORTB & _BV(PB3)));
    assert((DDRB & 0x17) == 0x17);

    PINB = _BV(PB3);
    Colour open = select_colour();
    PINB = 0;
    Colour closed = select_colour();
#if RGBW_MODE == 1
    assert(open.red == RGBW_OPEN_R && open.green == RGBW_OPEN_G &&
           open.blue == RGBW_OPEN_B && open.white == RGBW_OPEN_W);
    assert(closed.red == RGBW_BRIDGED_R && closed.green == RGBW_BRIDGED_G &&
           closed.blue == RGBW_BRIDGED_B && closed.white == RGBW_BRIDGED_W);
#else
    assert(open.red == RGBW_FIXED_R && open.green == RGBW_FIXED_G &&
           open.blue == RGBW_FIXED_B && open.white == RGBW_FIXED_W);
    assert(closed.red == open.red && closed.green == open.green &&
           closed.blue == open.blue && closed.white == open.white);
#endif

    reset_registers();
    start_pwm((Colour){0, 255, 0, 0});
    assert(!(PORTB & (_BV(PB0) | _BV(PB2) | _BV(PB4))));
    assert(PORTB & _BV(PB1));
    assert(!(TCCR0A & (_BV(COM0A1) | _BV(COM0B1))));
    assert(!(GTCCR & _BV(COM1B1)) && TIMSK == 0);

    reset_registers();
    start_pwm((Colour){255, 0, 255, 255});
    assert((PORTB & 0x17) == 0x15);
    assert(!(TCCR0A & (_BV(COM0A1) | _BV(COM0B1))));
    assert(!(GTCCR & _BV(COM1B1)) && TIMSK == 0);

    reset_registers();
    start_pwm((Colour){1, 128, 254, 128});
    assert(OCR0A == 1 && OCR0B == 128 && OCR1B == 254 && OCR1A == 128);
    assert(OCR1C == 255);
    assert((TCCR0A & (_BV(COM0A1) | _BV(COM0B1))) == (_BV(COM0A1) | _BV(COM0B1)));
    assert((GTCCR & (_BV(PWM1B) | _BV(COM1B1))) == (_BV(PWM1B) | _BV(COM1B1)));
    assert(TCCR0B == (_BV(CS01) | _BV(CS00)));
    assert(TCCR1 == (_BV(CS12) | _BV(CS11) | _BV(CS10)));
    assert(TIMSK == (_BV(TOIE1) | _BV(OCIE1A)));
    timer1_overflow();
    assert(PORTB & _BV(PB2));
    timer1_compare_a();
    assert(!(PORTB & _BV(PB2)));
    return 0;
}
