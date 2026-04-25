define double @float_ops(double %x, double %y) {
entry:
  %sum = fadd double %x, %y
  %prod = fmul double %sum, %x
  %cmp = fcmp ogt double %prod, 0.0
  br i1 %cmp, label %positive, label %negative

positive:
  %sqrt_approx = fmul double %prod, 0.5
  br label %done

negative:
  %abs = fsub double 0.0, %prod
  %abs = fsub double 0.0, %prod
  br label %done

done:
  %result = phi double [%sqrt_approx, %positive], [%abs, %negative]
  ret double %result
}
