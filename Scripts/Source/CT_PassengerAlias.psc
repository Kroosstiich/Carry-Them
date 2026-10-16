Scriptname CT_PassengerAlias extends ReferenceAlias
; The carried NPC: set down when they fight or die, brought along when the player changes cell.

Event OnCombatStateChanged(Actor akTarget, int aeCombatState)
	if aeCombatState != 0
		(GetOwningQuest() as CT_Control).Drop()
	endif
EndEvent

Event OnDeath(Actor akKiller)
	(GetOwningQuest() as CT_Control).Drop()
EndEvent

Event OnCellDetach()
	(GetOwningQuest() as CT_Control).FollowPlayer()
EndEvent
