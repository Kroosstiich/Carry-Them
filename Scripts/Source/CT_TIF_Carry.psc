;BEGIN FRAGMENT CODE - Do not edit anything between this and the end comment
;NEXT FRAGMENT INDEX 1
Scriptname CT_TIF_Carry Extends TopicInfo Hidden
; End fragment of "On my back." / "In my arms." (CarryThem - Dialogue.esp), told apart by Style.

;BEGIN FRAGMENT Fragment_0
Function Fragment_0(ObjectReference akSpeakerRef)
Actor akSpeaker = akSpeakerRef as Actor
;BEGIN CODE
Control.CarryAs(akSpeaker, Style)
;END CODE
EndFunction
;END FRAGMENT

;END FRAGMENT CODE - Do not edit anything between this and the begin comment

CT_Control Property Control Auto
int Property Style Auto ; 0 on the back, 1 in the arms
