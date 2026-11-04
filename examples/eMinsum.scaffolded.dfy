function sum(a: array<int>, i: int, j: int): int
  reads a
  requires 0 <= i <= j <= a.Length
  decreases j - i
{
  if j == i then 0 else sum(a, i, j - 1) + a[j - 1]
}

method MinSubarray(a: array<int>) returns (s: int)
  requires a.Length > 0
  ensures forall i, j :: 0 <= i < j <= a.Length ==> sum(a, i, j) >= s
{
  var m, c := 0, 0;
  s := 0;
  while m < a.Length
    invariant 0 <= m <= a.Length
    invariant forall i, j :: 0 <= i < j <= m ==> sum(a, i, j) >= s
    invariant forall i :: 0 <= i < m ==> sum(a, i, m) >= c
    decreases a.Length - m
  {
    c := if c + a[m] < a[m] then c + a[m] else a[m];
    s := if s < c then s else c;
    m := m + 1;
  }
}
