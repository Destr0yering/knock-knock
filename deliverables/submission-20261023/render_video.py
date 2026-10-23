import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).parent
d = json.loads((root / 'demo-output.json').read_text(encoding='utf-8-sig'))
fontpath = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
mono = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
def font(n, code=False):
    return ImageFont.truetype(mono if code else fontpath, n)
slides = [
 ('Knock Knock', 'Visitor awareness with household control',
  ['Actual backend simulator results captured October 23, 2026.',
   'Synthetic fixtures only. No private Ring footage or face data.',
   'This video demonstrates the backend workflow, not a live Ring link.'], None),
 ('One arrival. Three people.', 'A deterministic Ring-style button event enters the demo API.',
  ['The learning-period alert stays generic.', 'Each person has an independent review state.'],
  {k:d['visit'][k] for k in ['event_type','source','person_count','alert']}),
 ('Show uncertainty', 'A suggestion is not an identity verdict.',
  ['One advisory match, one unknown, and one face-undetected result.',
   'These scores come from synthetic fixtures, not live Rekognition.'],
  [{'person':p['id'],'state':p['review_state'],'suggested_name':p['suggested_name']} for p in d['visit']['people']]),
 ('Members propose. Owners decide.', 'The backend enforces the household role boundary.',
  ['A member submits a label proposal.', 'The same member cannot approve it.'],
  {'proposal_status':d['member_proposal']['proposal_status'],'member_approval_attempt':d['member_approval_attempt']}),
 ('Approval leaves a record', 'The owner confirms Taylor and the visit state updates.',
  ['Saved-media state and attributable audit events are returned.',
   'No automatic door unlocking or consequential action.'],
  {'decision':d['owner_approval']['proposal']['decision'],'decided_by':d['owner_approval']['proposal']['decided_by'],'profile_name':d['owner_approval']['profile_name'],'audit':d['audit_event_types']}),
 ('Built for Ring + AWS + Android', 'Implemented source includes the official Ring integration boundary.',
  ['Ring OAuth / signed events / snapshot processing',
   'API Gateway / Lambda / SQS / Rekognition / S3 / DynamoDB',
   'Kotlin / Compose / Room / Cognito / Firebase messaging',
   'Current Android debug APK assembled and signature-verified on Nano.'], None),
 ('Prototype status, stated plainly', 'What this demonstration proves - and what remains.',
  ['Proven here: synthetic event, separate reviews, role checks, approval, audit.',
   'Unverified: personal Ring linking, real snapshot recognition, FCM delivery.',
   'Privacy notice and cloud deletion exist in source; deployment is pending.',
   'Code and instructions: github.com/Destr0yering/knock-knock'], None),
]
thumbs=[]
for i,(title,sub,lines,code) in enumerate(slides):
    im=Image.new('RGB',(1920,1080),'#0b1425'); draw=ImageDraw.Draw(im)
    draw.rectangle((0,0,1920,14),fill='#40d4bd')
    draw.text((94,72),'KNOCK KNOCK  /  SYNTHETIC BACKEND DEMO',font=font(25),fill='#40d4bd')
    draw.text((90,142),title,font=font(63),fill='white')
    draw.text((94,238),sub,font=font(30),fill='#b8c9e2')
    y=310
    for line in lines:
        draw.text((98,y),line,font=font(28),fill='#e3ebf7'); y+=58
    if code is not None:
        text=json.dumps(code,indent=2)
        draw.rounded_rectangle((90,y+12,1830,986),radius=20,fill='#111f34')
        draw.multiline_text((122,y+32),text,font=font(26,True),fill='#96e9d8',spacing=7)
    draw.text((94,1024),'Actual run: scripts/run_local_demo.py | backend container checkpoint 2026-10-15',font=font(21),fill='#8da1bb')
    draw.text((1740,1020),f'{i+1} / 7',font=font(24),fill='#8da1bb')
    im.save(root/f'frame-{i:02}.png'); thumbs.append(im.resize((480,270)))
sheet=Image.new('RGB',(960,1080),'#0b1425')
for i,im in enumerate(thumbs): sheet.paste(im,((i%2)*480,(i//2)*270))
sheet.save(root/'contact-sheet.jpg')
