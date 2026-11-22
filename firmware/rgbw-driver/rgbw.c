#ifndef F_CPU
#error "Set F_CPU to the actual ATtiny85 clock frequency"
#endif

#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>
#include <util/delay.h>
#include "config.h"

typedef struct {
    uint8_t red, green, blue, white;
} Colour;

static void init_pins(void)
{
    PORTB &= (uint8_t)~(_BV(PB0) | _BV(PB1) | _BV(PB2) | _BV(PB3) | _BV(PB4));
    DDRB = (DDRB & (uint8_t)~_BV(PB3)) |
           _BV(PB0) | _BV(PB1) | _BV(PB2) | _BV(PB4);
}

static Colour select_colour(void)
{
#if RGBW_MODE == 1
    /* The board's external 100k pull-up defines an open JP1. */
    _delay_ms(20);
    if (!(PINB & _BV(PB3))) {
        return (Colour){RGBW_BRIDGED_R, RGBW_BRIDGED_G,
                        RGBW_BRIDGED_B, RGBW_BRIDGED_W};
    }
    return (Colour){RGBW_OPEN_R, RGBW_OPEN_G, RGBW_OPEN_B, RGBW_OPEN_W};
#else
    return (Colour){RGBW_FIXED_R, RGBW_FIXED_G, RGBW_FIXED_B, RGBW_FIXED_W};
#endif
}

static void start_pwm(Colour colour)
{
    /* Disconnect endpoint channels, avoiding narrow pulses at 0 and 255. */
    TCCR0A = _BV(WGM00) | _BV(WGM01);
    TCCR0B = 0;
    TCCR1 = 0;
    GTCCR = 0;
    TIMSK = 0;
    TCNT0 = 0;
    TCNT1 = 0;
    OCR0A = colour.red;
    OCR0B = colour.green;
    OCR1B = colour.blue;
    OCR1C = 255;
    OCR1A = colour.white;

    if (colour.red == 255) PORTB |= _BV(PB0);
    else if (colour.red != 0) TCCR0A |= _BV(COM0A1);
    if (colour.green == 255) PORTB |= _BV(PB1);
    else if (colour.green != 0) TCCR0A |= _BV(COM0B1);
    if (colour.blue == 255) PORTB |= _BV(PB4);
    GTCCR = _BV(PWM1B);
    if (colour.blue != 0 && colour.blue != 255) GTCCR |= _BV(COM1B1);

    if (colour.white == 255) {
        PORTB |= _BV(PB2);
    } else if (colour.white != 0) {
        TIFR = _BV(TOV1) | _BV(OCF1A);
        TIMSK = _BV(TOIE1) | _BV(OCIE1A);
    }

    /* Both timers use clk/64; Timer1 compare A drives software white PWM. */
    TCCR0B = _BV(CS01) | _BV(CS00);
    TCCR1 = _BV(CS12) | _BV(CS11) | _BV(CS10);
}

ISR(TIMER1_OVF_vect)
{
    PORTB |= _BV(PB2);
}

ISR(TIMER1_COMPA_vect)
{
    PORTB &= (uint8_t)~_BV(PB2);
}

int main(void)
{
    cli();
    init_pins();
    Colour colour = select_colour();
    start_pwm(colour);
    set_sleep_mode(SLEEP_MODE_IDLE);
    sei();
    for (;;) sleep_mode();
}
