method FindWindowBoundary(buffer: array<bv8>, windowStart: nat, windowEnd: nat, target: seq<bv8>) 
  returns (index: int)
  reads buffer
  requires buffer != null
  requires 0 <= windowStart <= windowEnd <= buffer.Length
  requires |target| > 0
{
  var i := 0;
  while i < buffer.Length
    invariant 0 <= i <= buffer.Length
    decreases buffer.Length - i
  {
    i := i + 1;
  }
}
