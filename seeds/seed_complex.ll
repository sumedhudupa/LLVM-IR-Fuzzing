; seeds/seed_complex.ll
; Complex stress seed:
; - Multiple functions
; - Loop PHI nodes and back-edges
; - Branching, select, switch
; - Bitwise + arithmetic mixes
; - Memory ops (alloca/load/store)

define i32 @mix(i32 %x, i32 %y) {
entry:
  %x1 = mul i32 %x, 31
  %y1 = add i32 %y, 17
  %z0 = xor i32 %x1, %y1
  %cmp = icmp sgt i32 %z0, 0
  br i1 %cmp, label %pos, label %neg

pos:
  %z1 = lshr i32 %z0, 1
  br label %join

neg:
  %z2 = sub i32 0, %z0
  br label %join

join:
  %z = phi i32 [ %z1, %pos ], [ %z2, %neg ]
  %masked = and i32 %z, 255
  ret i32 %masked
}

define i32 @accumulate(i32 %n) {
entry:
  %n_nonneg = select i1 (icmp sgt i32 %n, 0), i32 %n, i32 0
  br label %loop

loop:
  %i = phi i32 [ 0, %entry ], [ %i_next, %body ]
  %sum = phi i32 [ 0, %entry ], [ %sum_next, %body ]
  %cond = icmp slt i32 %i, %n_nonneg
  br i1 %cond, label %body, label %exit

body:
  %mixv = call i32 @mix(i32 %i, i32 %sum)
  %sum_next = add i32 %sum, %mixv
  %i_next = add i32 %i, 1
  br label %loop

exit:
  ret i32 %sum
}

define i32 @dispatch(i32 %v) {
entry:
  %mod = and i32 %v, 3
  switch i32 %mod, label %default [
    i32 0, label %c0
    i32 1, label %c1
    i32 2, label %c2
  ]

c0:
  %r0 = add i32 %v, 11
  br label %ret

c1:
  %r1 = sub i32 %v, 7
  br label %ret

c2:
  %r2 = xor i32 %v, 90
  br label %ret

default:
  %r3 = mul i32 %v, 3
  br label %ret

ret:
  %out = phi i32 [ %r0, %c0 ], [ %r1, %c1 ], [ %r2, %c2 ], [ %r3, %default ]
  ret i32 %out
}

define i32 @main() {
entry:
  %buf = alloca [4 x i32], align 16
  %p0 = getelementptr inbounds [4 x i32], ptr %buf, i32 0, i32 0
  %p1 = getelementptr inbounds [4 x i32], ptr %buf, i32 0, i32 1
  %p2 = getelementptr inbounds [4 x i32], ptr %buf, i32 0, i32 2
  %p3 = getelementptr inbounds [4 x i32], ptr %buf, i32 0, i32 3

  %a0 = call i32 @accumulate(i32 12)
  %a1 = call i32 @accumulate(i32 7)
  %d0 = call i32 @dispatch(i32 %a0)
  %d1 = call i32 @dispatch(i32 %a1)

  store i32 %a0, ptr %p0, align 4
  store i32 %a1, ptr %p1, align 4
  store i32 %d0, ptr %p2, align 4
  store i32 %d1, ptr %p3, align 4

  %l0 = load i32, ptr %p0, align 4
  %l1 = load i32, ptr %p1, align 4
  %l2 = load i32, ptr %p2, align 4
  %l3 = load i32, ptr %p3, align 4

  %t0 = add i32 %l0, %l1
  %t1 = xor i32 %l2, %l3
  %t2 = add i32 %t0, %t1
  %final = and i32 %t2, 1023
  ret i32 %final
}
