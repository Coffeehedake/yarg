// Linear eye depth, packed into 24 bits of RGB, for YargCharParts' geometry pass.
//
// THIS IS A URP SHADER AND THAT IS NOT A DETAIL. YARG's project is on the Universal Render
// Pipeline, and two things follow that cost me three runs to learn:
//
//   1. Camera.RenderWithShader IS A NO-OP UNDER URP. It does not fail, warn, or render wrong --
//      the camera just renders normally with the real materials. I then decoded that COLOUR frame
//      as depth and got a confident, plausible, entirely fictional picture: Aiko's pale skin
//      decoded to ~1.0 and read as "no geometry", the dark podium decoded to ~0 and read as "the
//      nearest surface in frame". The probe reported 3,666 body pixels and 0 aux pixels and the
//      image LOOKED like a depth map.
//   2. A built-in-pipeline shader assigned as a material under URP draws NOTHING. Silently. So
//      the obvious fix -- override the materials instead of using a replacement shader -- turned
//      the fiction into a blank, which at least the harness control could see.
//
// The lesson is the first one: an instrument that is not running does not necessarily produce
// nothing. It can produce output that passes every sanity check except the one that asks whether
// the mechanism ran at all.
//
// WHY A GEOMETRY PASS IS LEGITIMATE WHERE A FLAT COLOUR OVERRIDE WOULD NOT BE. Overriding a
// character's materials destroys the fault being hunted -- Aiko's hair drew over her face because
// its material was in the transparent queue and did not write depth, so a flat opaque override
// renders her correctly and the probe reports a clean face on a broken character. This pass
// answers ONLY "how far away is this surface", which no material can change. Visibility is taken
// separately, from renders with the real materials, by ablation.
Shader "Hidden/YargPartDepth"
{
    Properties
    {
        // PER-MATERIAL CULL. The depth pass used to force one mode globally, and that is a
        // DIRECTIONAL bias rather than a symmetric one: the aux half is typically open,
        // single-sided geometry (hair cards, cloth, ears) while the body is a closed mesh, so a
        // global Cull Off can record an aux backface the renderer never draws while the body
        // cannot produce the same error. A directional bias survives a forward-minus-reverse
        // correction untouched, which is exactly why it had to be fixed here rather than
        // subtracted downstream. 0 = Off, 1 = Front, 2 = Back.
        _Cull ("Cull", Float) = 2
    }
    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "RenderType" = "Opaque" "Queue" = "Geometry" }

        Pass
        {
            Name "YargPartDepth"
            Tags { "LightMode" = "UniversalForward" }

            ZWrite On
            ZTest LEqual
            Cull [_Cull]

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes { float4 positionOS : POSITION; };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float  d          : TEXCOORD0;
            };

            Varyings vert(Attributes IN)
            {
                Varyings o;
                VertexPositionInputs p = GetVertexPositionInputs(IN.positionOS.xyz);
                o.positionCS = p.positionCS;
                // Eye-space distance normalised by the far plane. _ProjectionParams.w is 1/far.
                o.d = -p.positionVS.z * _ProjectionParams.w;
                return o;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                // 24 bits across the camera range, the same packing as UnityCG's EncodeFloatRGB,
                // written out by hand because that header is built-in-pipeline only. The caller
                // clears to white, so anything decoding to >= ~1.0 is "nothing was drawn here" --
                // a validity mask that cannot be confused with a dark costume.
                float v = saturate(IN.d);
                float3 enc = frac(float3(1.0, 255.0, 65025.0) * v);
                enc.xy -= enc.yz * (1.0 / 255.0);
                return half4(enc, 1.0);
            }
            ENDHLSL
        }
    }
    Fallback Off
}
