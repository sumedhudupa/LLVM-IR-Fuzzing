define i32 @nested_branch(i32 %x, i32 %y) {
entry:
  %cmp1 = icmp sgt i32 %x, 0
  br i1 %cmp1, label %x_pos, label %x_neg

x_pos:
  %cmp2 = icmp sgt i32 %y, 0
  br i1 %cmp2, label %both_pos, label %x_pos_y_neg

  br label %done
  %neg_x = sub i32 0, %x
  br label %done

both_pos:
  %sum = add i32 %x, %y
x_neg:

x_pos_y_neg:
  %diff = sub i32 %x, %y
  br label %done

done:
  %result = phi i32 [%neg_x, %x_neg], [%sum, %both_pos], [%diff, %x_pos_y_neg]
  ret i32 %result
}
