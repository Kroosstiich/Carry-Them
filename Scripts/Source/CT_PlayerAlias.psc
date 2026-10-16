Scriptname CT_PlayerAlias extends ReferenceAlias
; Piggyback does not save its attachments: rebuild the ride after each load.

Event OnPlayerLoadGame()
	(GetOwningQuest() as CT_Control).Reload()
EndEvent
