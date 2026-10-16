Scriptname CT_HopOnEffect extends ActiveMagicEffect
; Effect of the "Carry Them" power: picks up the target, or sets the current rider down.

CT_Control Property Control Auto

Event OnEffectStart(Actor akTarget, Actor akCaster)
	Debug.Trace("[CarryThem] " + Utility.GetCurrentRealTime() + " power hit " + akTarget + " from " + akCaster)
	if akCaster == Game.GetPlayer()
		Control.Toggle(akTarget)
	endif
EndEvent
