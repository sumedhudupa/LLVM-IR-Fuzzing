; seed_branch.ll - Conditional branch + icmp
; Valid LLVM IR that passes llvm-as + opt -passes=verify

define i32 @main() {
entry:
  %a = alloca i32, align 4
  store i32 50, i32* %a, align 4
  %val = load i32, i32* %a, align 4
  %cmp = icmp sgt i32 %val, 25
  br i1 %cmp, label %if_true, label %if_false

if_true:
  %res1 = add i32 %val, 100
  br label %merge

if_false:
  %res2 = sub i32 %val, 10
  br label %merge

merge:
  %result = phi i32 [ %res1, %if_true ], [ %res2, %if_false ]
  ret i32 %result
}
