Scriptname CT_Control extends Quest
; Carry Them: the player carries an NPC on their back (the reverse of Carry Me), or in their arms.
; Piggyback glues the rider to the player's spine (or left forearm) every frame; OAR swaps in the poses:
; - the rider plays the "holding on" pose through its idle/walk/run animations (CT_CarriedAbility),
; - the player plays the carrying pose through Offset Movement Animation (CT_CarryingAbility).
; The princess carry has its own pose markers and offset globals (CT_Princess*).

Spell Property HopOnPower Auto
Spell Property CarriedAbility Auto
Spell Property CarryingAbility Auto
ReferenceAlias Property Passenger Auto
Actor Property PlayerRef Auto
Keyword Property ActorTypeNPC Auto
Message Property StyleMenu Auto ; On my back / In my arms / Cancel
GlobalVariable Property Hotkey Auto ; DirectX scan code, -1 or 0 = none: carries the NPC in the crosshair, or sets the rider down
Spell Property PrincessCarriedAbility Auto
Spell Property PrincessCarryingAbility Auto
float Property BehindDistance = 50.0 AutoReadOnly ; where the rider walks to before hopping on
; Rider offset from the anchor (X right, Y forward, Z up). Globals so they can be tuned from the
; console (set CT_OffsetZ to -8) and later by an MCM; read at each pick-up.
GlobalVariable Property OffsetX Auto
GlobalVariable Property OffsetY Auto
GlobalVariable Property OffsetZ Auto
GlobalVariable Property Rotation Auto ; rider facing vs the player's, degrees, clockwise seen from above
GlobalVariable Property PrincessOffsetX Auto
GlobalVariable Property PrincessOffsetY Auto
GlobalVariable Property PrincessOffsetZ Auto
GlobalVariable Property PrincessRotation Auto

int jumpKey
int hotkeyCode
; The current carry, saved with the game so a reload re-attaches it the same way (see UseStyle).
int style
string anchorNode
float offX
float offY
float offZ
float rotationDeg
Spell carriedSpell
Spell carryingSpell

Event OnInit()
	PlayerRef.AddSpell(HopOnPower, false)
	RegisterHotkey()
EndEvent

; Called at start, on each load and when the MCM closes.
Function RegisterHotkey()
	if hotkeyCode > 0 && hotkeyCode != jumpKey
		UnregisterForKey(hotkeyCode)
	endif
	hotkeyCode = Hotkey.GetValueInt()
	if hotkeyCode > 0
		RegisterForKey(hotkeyCode)
	endif
EndFunction

; Called on each load: gives the power back if the player lost it (a "forget all spells" mod, for instance).
Function GivePowers()
	if !PlayerRef.HasSpell(HopOnPower)
		PlayerRef.AddSpell(HopOnPower, false)
	endif
EndFunction

; Picks the anchor, offsets and pose markers of a carry style (0 on the back, 1 princess carry).
Function UseStyle(int aiStyle)
	style = aiStyle
	if aiStyle == 1 ; Carry Me's bridal carry: held on the left forearm, in front of the player
		anchorNode = "NPC L Forearm [LLAr]"
		offX = PrincessOffsetX.GetValue()
		offY = PrincessOffsetY.GetValue()
		offZ = PrincessOffsetZ.GetValue()
		rotationDeg = PrincessRotation.GetValue()
		carriedSpell = PrincessCarriedAbility
		carryingSpell = PrincessCarryingAbility
	else
		anchorNode = "NPC Spine2 [Spn2]"
		offX = OffsetX.GetValue()
		offY = OffsetY.GetValue()
		offZ = OffsetZ.GetValue()
		rotationDeg = Rotation.GetValue()
		carriedSpell = CarriedAbility
		carryingSpell = CarryingAbility
	endif
EndFunction

Function Log(string asMessage)
	Debug.Trace("[CarryThem] " + Utility.GetCurrentRealTime() + " " + asMessage)
EndFunction

; Called by the power: set the current rider down, or ask how to carry the target and carry it.
Function Toggle(Actor akTarget)
	Log("Toggle on " + akTarget + ", passenger " + Passenger.GetActorRef())
	if Passenger.GetActorRef()
		Drop()
	elseif CanCarry(akTarget)
		int choice = StyleMenu.Show() ; 0 on the back, 1 in the arms, 2 cancel: the button order is the style
		Log("Menu choice " + choice)
		if choice < 2
			CarryAs(akTarget, choice)
		endif
	endif
EndFunction

; Carries akTarget with a given style (0 on the back, 1 in the arms). Also called by the dialogue lines,
; which ask the style themselves. Checks again: the menu or the conversation took time.
Function CarryAs(Actor akTarget, int aiStyle)
	if !Passenger.GetActorRef() && CanCarry(akTarget)
		UseStyle(aiStyle)
		Carry(akTarget)
	endif
EndFunction

bool Function CanCarry(Actor akTarget)
	if Piggyback.GetVersion() < 10202 ; ApproachAndAttach, SetTurnSmoothing, SetRotationOffset
		Debug.Notification("$CT_NeedPiggyback")
	elseif !akTarget || akTarget == PlayerRef || akTarget.IsDead() || !akTarget.HasKeyword(ActorTypeNPC)
		Debug.Notification("$CT_CantCarryThat")
	elseif akTarget.IsInCombat() || akTarget.IsHostileToActor(PlayerRef)
		Debug.Notification("$CT_WontLetYou")
	elseif PlayerRef.IsWeaponDrawn() ; the weapon stayed in hand, and the carrying pose broke (raised arm)
		Debug.Notification("$CT_SheatheFirst")
	elseif akTarget.GetSitState() != 0 || akTarget.IsOnMount() || PlayerRef.IsOnMount() || PlayerRef.GetSitState() != 0
		Debug.Notification("$CT_CantCarryFromHere")
	else
		return true
	endif
	Log("CanCarry refused " + akTarget)
	return false
EndFunction

Function Carry(Actor akRider)
	Passenger.ForceRefTo(akRider)
	if akRider.IsWeaponDrawn()
		akRider.SheatheWeapon() ; it kept it in hand on the player's back
	endif
	; The rider walks to a spot behind the player (in front for the princess carry: a negative distance),
	; then hops on: no leap from wherever it stood. Latent, up to 8 s; the rider must still be free to
	; walk, so it is frozen only afterwards.
	float approach = BehindDistance
	if style == 1
		approach = -BehindDistance
	endif
	Log("Approach " + akRider)
	bool attached = Piggyback.ApproachAndAttach(akRider, PlayerRef, anchorNode, offX, offY, offZ, true, approach)
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
	Piggyback.Attach(akRider, PlayerRef, anchorNode, offX, offY, offZ, true)
	Settle(akRider)
EndFunction

; Everything that holds the rider on the back once attached, and that the save does not keep.
; Never EnableAI(false) on the rider: an actor without AI stops updating its 3D, so it stays drawn
; on the ground while Piggyback moves it onto the back (build 0.1.1-0.1.3).
Function Settle(Actor akRider)
	akRider.SetDontMove(true)
	; Pose markers before the pose reset and OffsetGPMA: OAR picks the replacement when the animation starts.
	akRider.AddSpell(carriedSpell, false)
	PlayerRef.AddSpell(carryingSpell, false)
	; Restrained, as RSE does for its passengers: the AI keeps running (head, 3D) but no longer tries
	; to walk, follow, sneak or play idles, which fought Piggyback and stood the rider up.
	akRider.SetRestrained(true)
	Debug.SendAnimationEvent(akRider, "IdleForceDefaultState") ; leave the walk, play the pose
	akRider.SetHeadTracking(false) ; it stared at the player's head, right under its face
	Piggyback.SetTurnSmoothing(akRider, false) ; sitting on the back: turn with the body, no lag
	Piggyback.SetRotationOffset(akRider, rotationDeg)
	; The running player kept bumping into the rider sitting on them (stand-ups, "watch it" lines).
	if Piggyback.GetVersion() >= 10300
		; Only the player and the rider ignore each other; both still collide with everyone else.
		Piggyback.SetRiderCollision(akRider, false)
		if style == 1
			Piggyback.SetReleaseOffset(akRider, 0.0, 60.0) ; set down in front, not through the player
		endif
	else
		; Older Piggyback. Trade-off: the player walks through other characters until the rider is set down.
		Piggyback.SetHostCollision(akRider, false)
	endif
	if PlayerRef.GetAnimationVariableBool("bGPMAInstalled")
		Debug.SendAnimationEvent(PlayerRef, "OffsetGPMA")
	else
		Debug.Notification("$CT_NeedOMA")
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
	if jumpKey != hotkeyCode
		UnregisterForKey(jumpKey) ; the hotkey stays registered
	endif
	Debug.SendAnimationEvent(PlayerRef, "OffsetGPMAStop")
	PlayerRef.RemoveSpell(carryingSpell)
	Game.EnablePlayerControls(false, true, false, false, false, false, false, false)
	if Piggyback.IsAttached(rider)
		Piggyback.Detach(rider)
		Utility.Wait(0.9) ; let the exit transition finish before the AI takes over
	endif
	rider.RemoveSpell(carriedSpell)
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
	if Utility.IsInMenuMode()
		return
	elseif keyCode == hotkeyCode
		if Passenger.GetActorRef()
			Drop()
		else
			Actor target = Game.GetCurrentCrosshairRef() as Actor
			if target
				Toggle(target)
			endif
		endif
	elseif keyCode == jumpKey && Passenger.GetActorRef()
		Drop()
	endif
EndEvent

; Called by the player alias after a save is loaded.
Function Reload()
	Actor rider = Passenger.GetActorRef()
	Log("Reload, passenger " + rider + ", style " + style)
	GivePowers()
	RegisterHotkey()
	if !rider
		return
	endif
	if !anchorNode ; carrying since a 1.0.x save: back carry, with the current settings
		UseStyle(0)
	endif
	if rider.Is3DLoaded() && !rider.IsDead() && rider.GetParentCell() == PlayerRef.GetParentCell()
		rider.EnableAI(true) ; same clean-up as in Drop
		Attach(rider)
	else
		Drop()
	endif
EndFunction
