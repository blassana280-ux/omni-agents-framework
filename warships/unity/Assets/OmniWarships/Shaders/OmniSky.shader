// OMNI WARSHIPS — ciel procédural (T-012) : dégradé zénith/horizon,
// disque solaire + halo, champ d'étoiles nocturne. Piloté par
// WeatherDirector (_SunDir, _NightFactor, _StarsStrength, couleurs).
Shader "OmniWarships/Sky"
{
    Properties
    {
        _ZenithColor ("Couleur zenith", Color) = (0.30, 0.50, 0.78, 1)
        _HorizonColor ("Couleur horizon", Color) = (0.55, 0.65, 0.75, 1)
        _SunColor ("Couleur soleil", Color) = (1.00, 0.96, 0.88, 1)
        _SunDir ("Direction soleil (normalisee)", Vector) = (0.4, 0.7, 0.6, 0)
        _NightFactor ("Facteur nuit 0..1", Float) = 0
        _StarsStrength ("Intensite etoiles 0..1", Float) = 0
    }
    SubShader
    {
        Tags { "Queue" = "Background" "RenderType" = "Background" "PreviewType" = "Skybox" }
        Pass
        {
            Cull Off
            ZWrite Off

            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"

            float4 _ZenithColor;
            float4 _HorizonColor;
            float4 _SunColor;
            float4 _SunDir;
            float _NightFactor;
            float _StarsStrength;

            struct appdata
            {
                float4 vertex : POSITION;
            };

            struct v2f
            {
                float4 pos : SV_POSITION;
                float3 dir : TEXCOORD0;
            };

            v2f vert(appdata v)
            {
                v2f o;
                o.pos = UnityObjectToClipPos(v.vertex);
                // boite du skybox centree sur la camera : direction monde
                o.dir = mul((float3x3)unity_ObjectToWorld, v.vertex.xyz);
                return o;
            }

            float hash3(float3 p)
            {
                p = frac(p * 0.3183099 + 0.1);
                p *= 17.0;
                return frac(p.x * p.y * p.z * (p.x + p.y + p.z));
            }

            fixed4 frag(v2f i) : SV_Target
            {
                float3 d = normalize(i.dir);

                // degrade : horizon vers zenith
                float t = saturate(d.y);
                float horizon = pow(1.0 - t, 3.0);
                float3 col = lerp(_ZenithColor.rgb, _HorizonColor.rgb, horizon);

                // soleil : disque net + halo doux
                float sd = saturate(dot(d, normalize(_SunDir.xyz)));
                float disc = smoothstep(0.9993, 0.9997, sd);
                float halo = pow(sd, 64.0) * 0.35;
                col += _SunColor.rgb * (disc * 2.5 + halo) * (1.0 - _NightFactor * 0.6);

                // etoiles : cellules rares avec scintillement
                if (_StarsStrength > 0.01 && d.y > 0.0)
                {
                    float3 cell = floor(d * 160.0);
                    float h = hash3(cell);
                    float3 centerPos = (cell + 0.5) / 160.0;
                    float distToStar = length(d - centerPos);
                    float star = smoothstep(0.0025, 0.0, distToStar) * step(0.992, h);
                    col += star * _StarsStrength *
                        (0.55 + 0.45 * sin(_Time.y * 2.0 + h * 40.0));
                }

                // assombrissement nocturne global
                col *= lerp(1.0, 0.55, _NightFactor);
                return fixed4(col, 1.0);
            }
            ENDCG
        }
    }
    Fallback Off
}
