using System.Collections.Generic;

namespace OmniWarships.Core.Spec
{
    public sealed class CompartmentSpec
    {
        public string Id;
        public float Center;    // position le long de la coque, 0 = proue, 1 = poupe
        public float Half;      // demi-etendue le long de la coque
        public float Hp;
        public float Armor;     // multiplicateur > 1 : divise les degats
        public ShipSystemKind[] Systems;

        public bool Covers(float along)
        {
            return along >= Center - Half && along <= Center + Half;
        }
    }

    /// <summary>Etat d'un compartiment pendant la bataille.</summary>
    public sealed class CompartmentState
    {
        public string Id;
        public float Hp;
        public float HpMax;
        public float Flooding;   // 0..1
        public bool Breached;
        public bool Destroyed;
    }
}
