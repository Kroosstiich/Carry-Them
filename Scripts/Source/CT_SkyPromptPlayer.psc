Scriptname CT_SkyPromptPlayer extends ReferenceAlias
; Player alias of CT_SkyPromptQuest: registers again with SkyPrompt after each load.

Event OnPlayerLoadGame()
	(GetOwningQuest() as CT_SkyPrompt).Init()
EndEvent
