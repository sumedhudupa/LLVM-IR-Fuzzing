define double @float_432(double %x, double %y) {
entry:
  %sum = fadd double %x, %y
  %prod = fmul fast double %sum, %x
  %cmp = fcmp ogt double %prod, 0.0
  br i1 %cmp, label %pos, label %neg

pos:
  %half = fmul double %prod, 0.5
  br label %done

neg:
  %abs_val = fsub double 0.0, %prod
  br label %done

done:
  %result = phi double [%half, %pos], [%abs_val, %neg]
  ret double %result
}
