Scriptname CT_Control extends Quest
; Carry Them: the player carries an NPC on their back (the reverse of Carry Me).
; Piggyback glues the rider to the player's spine every frame; OAR swaps in the poses:
; - the rider plays the "holding on" pose through its idle/walk/run animations (CT_CarriedAbility),
; - the player plays the carrying pose through Offset Movement Animation (CT_CarryingAbility).

Spell Property HopOnPower Auto
Spell Property CarriedAbility Auto
Spell Property CarryingAbility Auto
ReferenceAlias Property Passenger Auto
Actor Property PlayerRef Auto
Keyword Property ActorTypeNPC Auto
string Property AnchorNode = "NPC Spine2 [Spn2]" AutoReadOnly
float Property BehindDistance = 50.0 AutoReadOnly ; where the rider walks to before hopping on
; Rider offset from the anchor (X right, Y forward, Z up). Globals so they can be tuned from the
; console (set CT_OffsetZ to -8) and later by an MCM; read at each pick-up.
GlobalVariable Property OffsetX Auto
GlobalVariable Property OffsetY Auto
GlobalVariable Property OffsetZ Auto
GlobalVariable Property Rotation Auto ; rider facing vs the player's, degrees, clockwise seen from above

int jumpKey

Event OnInit()
	PlayerRef.AddSpell(HopOnPower, false)
EndEvent

Function Log(string asMessage)
	Debug.Trace("[CarryThem] " + Utility.GetCurrentRealTime() + " " + asMessage)
EndFunction

; Called by the power: carry the target, or set the current rider down.
Function Toggle(Actor akTarget)
	Log("Toggle on " + akTarget + ", passenger " + Passenger.GetActorRef())
	if Passenger.GetActorRef()
		Drop()
	elseif CanCarry(akTarget)
		Carry(akTarget)
	endif
EndFunction

bool Function CanCarry(Actor akTarget)
	if Piggyback.GetVersion() < 10202 ; ApproachAndAttach, SetTurnSmoothing, SetRotationOffset
		Debug.Notification("Carry Them needs Piggyback 1.2.2 or later.")
	elseif !akTarget || akTarget == PlayerRef || akTarget.IsDead() || !akTarget.HasKeyword(ActorTypeNPC)
		Debug.Notification("You can't carry that.")
	elseif akTarget.IsInCombat() || akTarget.IsHostileToActor(PlayerRef)
		Debug.Notification("They won't let you carry them now.")
	elseif akTarget.GetSitState() != 0 || akTarget.IsOnMount() || PlayerRef.IsOnMount() || PlayerRef.GetSitState() != 0
		Debug.Notification("You can't carry anyone from here.")
	else
		return true
	endif
	Log("CanCarry refused " + akTarget)
	return false
EndFunction

Function Carry(Actor akRider)
	Passenger.ForceRefTo(akRider)
	; The rider walks to a spot behind the player (game AI), then hops on: no leap from wherever it
	; stood. Latent, up to 8 s; the rider must still be free to walk, so it is frozen only afterwards.
	Log("Approach " + akRider)
	bool attached = Piggyback.ApproachAndAttach(akRider, PlayerRef, AnchorNode, OffsetX.GetValue(), OffsetY.GetValue(), OffsetZ.GetValue(), true, BehindDistance)
	if Passenger.GetActorRef() != akRider
		Log("Carry cancelled during the approach")
		if attached
			Piggyback.Detach(akRider) ; set down (power used again, combat...) while it was walking
		endif
		return
	elseif !attached
		Log("Approach failed")
		Passenger.Clear()
		return
	endif
	Settle(akRider)
	Game.DisablePlayerControls(false, true, false, false, false, false, false, false)
	Log("Carry done")
EndFunction

; Re-attach after a load: the save does not keep the Piggyback rig.
Function Attach(Actor akRider)
	Log("Attach " + akRider)
	Piggyback.Attach(akRider, PlayerRef, AnchorNode, OffsetX.GetValue(), OffsetY.GetValue(), OffsetZ.GetValue(), true)
	Settle(akRider)
EndFunction

; Everything that holds the rider on the back once attached, and that the save does not keep.
; Never EnableAI(false) on the rider: an actor without AI stops updating its 3D, so it stays drawn
; on the ground while Piggyback moves it onto the back (build 0.1.1-0.1.3).
Function Settle(Actor akRider)
	akRider.SetDontMove(true)
	; Pose markers before the pose reset and OffsetGPMA: OAR picks the replacement when the animation starts.
	akRider.AddSpell(CarriedAbility, false)
	PlayerRef.AddSpell(CarryingAbility, false)
	; Restrained, as RSE does for its passengers: the AI keeps running (head, 3D) but no longer tries
	; to walk, follow, sneak or play idles, which fought Piggyback and stood the rider up.
	akRider.SetRestrained(true)
	Debug.SendAnimationEvent(akRider, "IdleForceDefaultState") ; leave the walk, play the pose
	akRider.SetHeadTracking(false) ; it stared at the player's head, right under its face
	Piggyback.SetTurnSmoothing(akRider, false) ; sitting on the back: turn with the body, no lag
	Piggyback.SetRotationOffset(akRider, Rotation.GetValue())
	; The running player kept bumping into the rider sitting on them (stand-ups, "watch it" lines).
	; Trade-off: the player walks through other characters until the rider is set down.
	Piggyback.SetHostCollision(akRider, false)
	if PlayerRef.GetAnimationVariableBool("bGPMAInstalled")
		Debug.SendAnimationEvent(PlayerRef, "OffsetGPMA")
	else
		Debug.Notification("Carry Them needs Offset Movement Animation (run Nemesis or Pandora).")
	endif
	jumpKey = Input.GetMappedKey("Jump")
	RegisterForKey(jumpKey)
EndFunction

Function Drop()
	Actor rider = Passenger.GetActorRef()
	if !rider
		return
	endif
	Passenger.Clear() ; first, so a second Drop arriving during the wait below does nothing
	Log("Drop " + rider)
	UnregisterForAllKeys()
	Debug.SendAnimationEvent(PlayerRef, "OffsetGPMAStop")
	PlayerRef.RemoveSpell(CarryingAbility)
	Game.EnablePlayerControls(false, true, false, false, false, false, false, false)
	if Piggyback.IsAttached(rider)
		Piggyback.Detach(rider)
		Utility.Wait(0.9) ; let the exit transition finish before the AI takes over
	endif
	rider.RemoveSpell(CarriedAbility)
	rider.SetRestrained(false)
	rider.SetHeadTracking(true)
	rider.SetDontMove(false)
	rider.EnableAI(true) ; saves from builds 0.1.1-0.1.3 may hold the rider with its AI off
	Log("Drop done " + rider)
EndFunction

; The rider's cell was unloaded (load door, fast travel): bring it to the player. It stays attached,
; and Piggyback puts it back on the back as soon as its 3D is loaded next to the player.
Function FollowPlayer()
	Actor rider = Passenger.GetActorRef()
	if !rider || rider.IsDead()
		return
	endif
	Log("FollowPlayer " + rider)
	rider.MoveTo(PlayerRef)
	Debug.SendAnimationEvent(PlayerRef, "OffsetGPMA") ; the carrying pose, in case the load reset it
EndFunction

Event OnKeyDown(int keyCode)
	if keyCode == jumpKey && !Utility.IsInMenuMode()
		Drop()
	endif
EndEvent

; Called by the player alias after a save is loaded.
Function Reload()
	Actor rider = Passenger.GetActorRef()
	Log("Reload, passenger " + rider)
	if !rider
		return
	endif
	if rider.Is3DLoaded() && !rider.IsDead() && rider.GetParentCell() == PlayerRef.GetParentCell()
		rider.EnableAI(true) ; same clean-up as in Drop
		Attach(rider)
	else
		Drop()
	endif
EndFunction
