define i32 @mem_173(ptr %arr, i32 %idx, i32 %val) {
entry:
  %ptr = getelementptr i32, ptr %arr, i32 %idx
  %old = load i32, ptr %ptr, align 4
  %sum = add i32 %old, %val
  %cmp = icmp sgt i32 %sum, 100
  br i1 %cmp, label %cap, label %store

cap:
  br label %store

store:
  %to_store = phi i32 [100, %cap], [%sum, %entry]
  store i32 %to_store, ptr %ptr, align 4
  ret i32 %to_store
}
