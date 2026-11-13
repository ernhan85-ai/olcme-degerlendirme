import json, random
from PIL import Image, ImageDraw, ImageFont
W,H=1240,1754
img=Image.new("RGB",(W,H),(252,251,247)); d=ImageDraw.Draw(img)
for y in range(140,H,56): d.line([(60,y),(W-60,y)],fill=(220,228,240),width=1)
f=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Oblique.ttf",46)
hdr=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",34)
d.text((80,60),"1) 3x + 5 = 20 denklemini çözünüz.",font=hdr,fill=(30,30,30))
steps=["3x + 5 = 20","3x = 20 + 5","3x = 25","x = 25/3"]
resp_steps=[]; y=180
for i,s in enumerate(steps):
    x=110+random.randint(-6,6)
    d.text((x,y),s,font=f,fill=(25,45,120))
    bb=d.textbbox((x,y),s,font=f)
    resp_steps.append({"raw_text":s.replace(" ",""),"ocr_confidence":[0.97,0.91,0.94,0.88][i],"page":1,
      "bbox":[(bb[0]-12)/W,(bb[1]-10)/H,(bb[2]+12)/W,(bb[3]+10)/H]})
    y+=95
d.rectangle([700,560,1100,660],outline=(40,40,40),width=2); d.text((715,520),"Cevap:",font=hdr,fill=(30,30,30))
d.text((740,585),"x = 25/3",font=f,fill=(25,45,120))
img.save("1005_sayfa1.png")
fx={"responses":[{"position":1,"final_answer":"x=25/3","answer_confidence":0.93,"page":1,"bbox":[700/W,560/H,1100/W,660/H],"steps":resp_steps}]}
open("1005.transcript.json","w").write(json.dumps(fx))
