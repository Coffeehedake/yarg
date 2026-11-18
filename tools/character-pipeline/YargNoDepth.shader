// Reproduces Aiko's bug ON PURPOSE, as the synthetic positive control for YargCharParts.
//
// An unlit material in the TRANSPARENT queue with ZWrite OFF -- which is what `alphaMode: BLEND`
// gets a character in Unity, and why her hair drew over her face: a surface that does not write
// depth is composited on top of whatever was already there, however far behind it the geometry
// actually is.
//
// URP, for the same reason as YargPartDepth.shader: a built-in-pipeline shader assigned as a
// material in this project renders NOTHING, silently, so the control would have constructed no
// fault at all and the "synthetic positive" would have reported a clean character.
//
// WHY THE CONTROL NEEDS ITS OWN SHADER. The obvious synthetic control -- shove the hair toward the
// camera and watch the number rise -- tests the WRONG THING. Hair moved in front of the face is
// legitimately in front of it, the depth pass agrees it is nearer, and the depth-order test
// correctly reports nothing. A probe validated that way would have been validated against a case
// it is supposed to ignore. The fault being hunted is not "hair in front of a face", it is "hair
// drawn in front of a face it is BEHIND", so the control has to break the DEPTH WRITE and then
// move the geometry BACKWARD.
Shader "Hidden/YargNoDepth"
{
    Properties
    {
        _Color ("Colour", Color) = (1, 0.2, 0.8, 0.9)
    }
    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "Queue" = "Transparent" "RenderType" = "Transparent" }

        Pass
        {
            Name "YargNoDepth"
            Tags { "LightMode" = "UniversalForward" }

            ZWrite Off
            ZTest Always
            Cull Off
            Blend SrcAlpha OneMinusSrcAlpha

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _Color;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings   { float4 positionCS : SV_POSITION; };

            Varyings vert(Attributes IN)
            {
                Varyings o;
                o.positionCS = GetVertexPositionInputs(IN.positionOS.xyz).positionCS;
                return o;
            }

            half4 frag(Varyings IN) : SV_Target { return _Color; }
            ENDHLSL
        }
    }
    Fallback Off
}
