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
  
}