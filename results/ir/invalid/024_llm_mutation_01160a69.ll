define i32 @switch_484(i32 %op, i32 %a, i32 %b) {
entry:
  switch i32 %op, label %default [
    i32 0, label %add_case
    i32 1, label %sub_case
    i32 2, label %mul_case
    i32 3, label %div_case
  ]

add_case:
  %r0 = add i32 %a, %b
  br label %done

sub_case:
  %r1 = sub i32 %a, %b
  br label %done

mul_case:
  %r2 = mul i32 %a, %b
  br label %done

div_case:
  %cmp = icmp eq i32 %b, 0
  br i1 %cmp, label %default, label %safe_div

safe_div:
  %r3 = sdiv i32 %a, %b
  br label %done

default:
  br label %done

done:
  %result = phi i32 [%r0, %add_case], [%r1, %sub_case], [%r2, %mul_case], [%r3, %safe_div], [0, %default]
  ret i32 %result
}
