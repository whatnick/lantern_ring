#ifndef MOCK_AVR_IO_H
#define MOCK_AVR_IO_H
#include <stdint.h>
#define _BV(n) (1U << (n))
enum { PB0, PB1, PB2, PB3, PB4 };
enum { WGM00, WGM01, COM0B1 = 5, COM0A1 = 7 };
enum { CS00, CS01, CS10 = 0, CS11, CS12 };
enum { PWM1B = 6, COM1B1 = 5 };
enum { TOIE1 = 2, OCIE1A = 6, TOV1 = 2, OCF1A = 6 };
extern uint8_t PORTB, DDRB, PINB, TCCR0A, TCCR0B, TCCR1, GTCCR, TIMSK;
extern uint8_t TCNT0, TCNT1, OCR0A, OCR0B, OCR1A, OCR1B, OCR1C, TIFR;
#endif
