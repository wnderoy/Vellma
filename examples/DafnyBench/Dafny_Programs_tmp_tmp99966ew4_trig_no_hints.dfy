predicate P(x: int)

predicate Q(x: int)

method test()
    requires forall x {
} :: P(x) && Q(x)
    ensures Q(0)
{
}
