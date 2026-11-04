method M()
{
}


method N()
  ensures (forall b: bool :: b || !b) || 2 != 2;

