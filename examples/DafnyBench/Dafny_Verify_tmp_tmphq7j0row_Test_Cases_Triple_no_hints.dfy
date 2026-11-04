method Triple(x: int) returns (r: int)
{
}

method TripleIf(x: int) returns (r: int) {
}

method TripleOver(x: int) returns (r: int) {
}

method TripleConditions(x: int) returns (r: int) 
requires x % 2 == 0
ensures r == 3 * x
{
}

method Caller() {
}

