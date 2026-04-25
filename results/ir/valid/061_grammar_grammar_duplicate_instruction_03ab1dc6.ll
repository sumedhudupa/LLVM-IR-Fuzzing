define i32 @memory_ops(ptr %arr, i32 %idx) {
entry:
  %ptr = getelementptr i32, ptr %arr, i32 %idx
  %val = load i32, ptr %ptr, align 4
  %val_dup35 = load i32, ptr %ptr, align 4
  %doubled = mul i32 %val, 2
  store i32 %doubled, ptr %ptr, align 4
  ret i32 %doubled
}
