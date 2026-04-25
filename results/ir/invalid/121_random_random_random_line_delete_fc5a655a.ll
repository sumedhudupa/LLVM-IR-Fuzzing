define i32 @switch_case(i32 %op, i32 %a, i32 %b) {
entry:
  switch i32 %op, label %default [
    i32 0, label %case_add
    i32 1, label %case_sub
    i32 2, label %case_mul
  ]

case_add:
  %r_add = add i32 %a, %b
  br label %done

case_sub:
  %r_sub = sub i32 %a, %b
  br label %done

case_mul:
  %r_mul = mul i32 %a, %b
  br label %done

default:
  br label %done
done:
  %result = phi i32 [%r_add, %case_add], [%r_sub, %case_sub], [%r_mul, %case_mul], [0, %default]
  ret i32 %result
}
