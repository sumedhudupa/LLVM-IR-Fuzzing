; ModuleID = 'seed_bitwise.ll'
; Test Case 5: Bitwise Operations
; Expected exit code: 63
;   255 & 15 = 15
;   15 | 240 = 255
;   255 ^ 128 = 127
;   127 << 1 = 254
;   254 >> 2 = 63
; Tests: bitwise opcode swaps (and↔or, xor→or), type consistency

define i32 @main() {
entry:
  %a = and i32 255, 15
  %b = or i32 %a, 240
  %c = xor i32 %b, 128
  %d = shl i32 %c, 1
  %e = lshr i32 %d, 2
  ret i32 %e
}
