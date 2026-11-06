// OMNI WARSHIPS - ocean Gerstner 4 composantes (URP).
// Le vertex shader duplique la formule du noyau (OceanModel.HeightAt) :
// memes amplitudes/longueurs/directions/phases passes par le CPU depuis la
// meme graine. La flottabilite des navires reste au CPU (source unique).
Shader "OmniWarships/Ocean"
{
    Properties
    {
        _DeepColor("Couleur eau profonde", Color) = (0.008, 0.06, 0.12, 1)
        _CrestColor("Couleur crete", Color) = (0.10, 0.38, 0.45, 1)
        _FoamColor("Couleur ecume", Color) = (0.85, 0.92, 0.95, 1)
        _HorizonColor("Couleur horizon", Color) = (0.55, 0.65, 0.75, 1)
        _Amp("Amplitudes x4", Vector) = (0.88, 0.72, 0.57, 0.41)
        _WaveLen("Longueurs d'onde x4", Vector) = (45, 75, 105, 135)
        _DirDeg("Directions degres x4", Vector) = (0, 0, 0, 0)
        _Phase("Phases x4", Vector) = (0, 0, 0, 0)
        _SunDir("Direction soleil (xyz)", Vector) = (0.42, 0.68, 0.61, 0)
        _FoamThreshold("Seuil ecume", Float) = 0.65
        _TimeScale("Echelle temps", Float) = 1.0
    }
    SubShader
    {
        Tags { "RenderPipeline"="UniversalPipeline" "RenderType"="Opaque" "Queue"="Geometry" }
        Pass
        {
            Name "ForwardOcean"
            Tags { "LightMode"="UniversalForward" }
            Cull Off

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.0

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _DeepColor;
                half4 _CrestColor;
                half4 _FoamColor;
                half4 _HorizonColor;
                half4 _Amp;
                half4 _WaveLen;
                half4 _DirDeg;
                half4 _Phase;
                half4 _SunDir;
                half _FoamThreshold;
                half _TimeScale;
            CBUFFER_END

            struct Attributes
            {
                float4 positionOS : POSITION;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 worldPos : TEXCOORD0;
                float waveH : TEXCOORD1;
                float3 normalW : TEXCOORD2;
            };

            float2 DirDegToVec(float deg)
            {
                float r = deg * 3.14159265 / 180.0;
                return float2(sin(r), cos(r));
            }

            float WaveHeight(float2 wp, float t, out float2 grad)
            {
                float h = 0.0;
                grad = float2(0.0, 0.0);
                [unroll]
                for (int i = 0; i < 4; i++)
                {
                    float wl = _WaveLen[i];
                    float k = 6.2831853 / wl;
                    float2 d = DirDegToVec(_DirDeg[i]);
                    float speed = sqrt(6.25 * wl);
                    float ph = k * dot(d, wp) - k * speed * t + _Phase[i];
                    h += _Amp[i] * sin(ph);
                    grad += _Amp[i] * cos(ph) * k * d;
                }
                return h;
            }

            Varyings vert(Attributes IN)
            {
                Varyings o;
                float3 wp = TransformObjectToWorld(IN.positionOS.xyz);
                float t = _Time.y * _TimeScale;
                float2 grad;
                float h = WaveHeight(wp.xz, t, grad);
                wp.y += h;
                o.positionCS = TransformWorldToHClip(wp);
                o.worldPos = wp;
                o.waveH = h;
                o.normalW = normalize(float3(-grad.x, 1.0, -grad.y));
                return o;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                half nh = saturate(IN.waveH * 0.5 + 0.5);
                half3 col = lerp(_DeepColor.rgb, _CrestColor.rgb, nh);

                // ecume sur les cretes + micro-variation sans texture
                half crest = saturate((IN.waveH - _FoamThreshold) * 2.0);
                half sparkle = frac(sin(dot(floor(IN.worldPos.xz * 4.0), float2(12.9898, 78.233))) * 43758.5453);
                col = lerp(col, _FoamColor.rgb, crest * (0.55 + 0.45 * sparkle));

                // speculaire soleil (Blinn-Phong)
                float3 viewDir = normalize(_WorldSpaceCameraPos - IN.worldPos);
                float3 halfDir = normalize(normalize(_SunDir.xyz) + viewDir);
                half spec = pow(max(dot(IN.normalW, halfDir), 0.0), 120.0);
                col += _FoamColor.rgb * spec * 0.8;

                // fondu horizon
                half dist = length(_WorldSpaceCameraPos - IN.worldPos);
                col = lerp(col, _HorizonColor.rgb, saturate(dist / 4200.0));

                return half4(col, 1.0);
            }
            ENDHLSL
        }
    }
}
