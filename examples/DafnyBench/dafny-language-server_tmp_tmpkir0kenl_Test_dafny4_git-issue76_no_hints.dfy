// RUN: %dafny  /compile:3 "%s" > "%t"
// RUN: %diff "%s.expect" "%t"

method Main() {
}

// The verification of the following methods requires knowledge
// about the injectivity of sequence displays.

method M0()
{
}

method M1()
{
}

method EqualityOfStrings0() {
}

method EqualityOfStrings1() {
}

method M2()
{
}

method M3()
{
}

