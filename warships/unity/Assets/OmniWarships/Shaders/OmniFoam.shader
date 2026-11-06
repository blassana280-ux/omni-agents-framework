// OMNI WARSHIPS — ecume (T-012) : nappe transparante animée (nappes
// concentriques + bruit de sin), fondu radial, pilote par _Intensity.
// Utilise la position objet du quad (EffectsPool.QuadMesh n'a pas d'UV).
Shader "OmniWarships/Foam"
{
    Properties
    {
        _TintColor ("Teinte ecume", Color) = (0.92, 0.96, 1.0, 0.85)
        _Intensity ("Intensite", Float) = 1.0
    }
    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Transparent"
               "RenderPipeline" = "UniversalPipeline" "IgnoreProjection" = "True" }
        Pass
        {
            Name "Unlit"
            Tags { "LightMode" = "SRPDefaultUnlit" }
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            Cull Off

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _TintColor;
                float _Intensity;
            CBUFFER_END

            struct Attributes
            {
                float4 positionOS : POSITION;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 objPos : TEXCOORD0;
                float4 worldPos : TEXCOORD1;
            };

            Varyings vert(Attributes input)
            {
                Varyings output;
                output.positionCS = TransformObjectToHClip(input.positionOS.xyz);
                output.objPos = input.positionOS.xz; // quad : [-0.5, 0.5]
                output.worldPos = mul(unity_ObjectToWorld, input.positionOS);
                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                // motif d'ecume : nappes concentriques + croisement de sin
                float r = length(input.objPos);
                float rings = 0.5 + 0.5 * sin(r * 28.0 - _Time.y * 6.0);
                float n = sin(input.worldPos.x * 1.7 + _Time.y * 2.0) *
                          sin(input.worldPos.z * 2.3 - _Time.y * 1.7);
                float foam = saturate(rings * 0.6 + 0.4 + n * 0.3);

                // fondu radial : coeur opaque, bord translucide
                float edge = 1.0 - smoothstep(0.25, 0.5, r);
                float alpha = _TintColor.a * edge * (0.35 + 0.65 * foam) * saturate(_Intensity);
                half3 rgb = _TintColor.rgb * (0.8 + 0.4 * foam);
                return half4(rgb, alpha);
            }
            ENDHLSL
        }
    }
    Fallback Off
}
