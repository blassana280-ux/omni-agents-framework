using System;

namespace OmniWarships.Core.Common
{
    /// <summary>Vecteur 2D deterministe (simulation navale, plan horizontal).</summary>
    public struct Vec2
    {
        public float X;
        public float Y;

        public Vec2(float x, float y) { X = x; Y = y; }

        public static Vec2 Zero { get { return new Vec2(0f, 0f); } }

        public float Length { get { return (float)Math.Sqrt(X * X + Y * Y); } }
        public float SqrLength { get { return X * X + Y * Y; } }

        public static Vec2 operator +(Vec2 a, Vec2 b) { return new Vec2(a.X + b.X, a.Y + b.Y); }
        public static Vec2 operator -(Vec2 a, Vec2 b) { return new Vec2(a.X - b.X, a.Y - b.Y); }
        public static Vec2 operator *(Vec2 a, float f) { return new Vec2(a.X * f, a.Y * f); }
        public static Vec2 operator -(Vec2 a) { return new Vec2(-a.X, -a.Y); }

        public static float Dot(Vec2 a, Vec2 b) { return a.X * b.X + a.Y * b.Y; }
        public static float Distance(Vec2 a, Vec2 b)
        {
            float dx = a.X - b.X, dy = a.Y - b.Y;
            return (float)Math.Sqrt(dx * dx + dy * dy);
        }

        public Vec2 Normalized()
        {
            float len = Length;
            if (len < 1e-9f) return Zero;
            return new Vec2(X / len, Y / len);
        }

        /// <summary>Cap en degres [0, 360) du vecteur (0 = nord/axe +Y).</summary>
        public float HeadingDeg()
        {
            float h = (float)(Math.Atan2(X, Y) * 180.0 / Math.PI);
            if (h < 0f) h += 360f;
            return h;
        }

        /// <summary>Vecteur unitaire pointant vers le cap donne (0 = nord/axe +Y).</summary>
        public static Vec2 FromHeadingDeg(float headingDeg)
        {
            double r = headingDeg * Math.PI / 180.0;
            return new Vec2((float)Math.Sin(r), (float)Math.Cos(r));
        }

        public Vec2 RotatedDeg(float deg)
        {
            double r = deg * Math.PI / 180.0;
            float c = (float)Math.Cos(r), s = (float)Math.Sin(r);
            return new Vec2(X * c - Y * s, X * s + Y * c);
        }
    }
}
