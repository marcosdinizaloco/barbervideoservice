import cv2, numpy as np, math
OUT_W,OUT_H=1080,1920; FPS_OUT=30.0
RASCUNHO_DUR=101.509; N_OUT=int(RASCUNHO_DUR*FPS_OUT)
GX,GY,GW,GH=326,372,408,986
SHOTS=[( 0.0,8.0,0.965,0.985,-1.0,-0.6,-4,2,3,0,1.000,1.008,0.99),
( 8.0,22.0,1.040,1.055,0.5,0.9,6,-4,-2,1,1.000,1.006,1.00),
(22.0,38.0,0.965,0.985,-0.9,-0.4,-8,8,2,-2,1.000,1.004,0.985),
(38.0,54.0,1.045,1.065,0.8,0.4,5,-5,-3,2,1.002,1.010,1.01),
(54.0,70.0,0.990,1.005,-0.6,0.2,-6,6,1,-2,1.000,1.006,0.995),
(70.0,81.0,1.000,1.020,0.3,0.0,3,0,0,-3,1.000,1.010,1.00),
(81.0,93.0,1.095,1.120,0.0,-0.3,0,-3,-4,-1,1.004,1.020,1.03),
(93.0,101.6,1.030,0.970,-0.2,0.5,-2,2,-1,2,1.010,1.000,0.985)]
P_a=np.zeros(N_OUT,np.float32);TH_a=np.zeros(N_OUT,np.float32)
LX_a=np.zeros(N_OUT,np.float32);VY_a=np.zeros(N_OUT,np.float32)
Z_a=np.zeros(N_OUT,np.float32);EX_a=np.ones(N_OUT,np.float32)
t_arr=np.arange(N_OUT,dtype=np.float32)/FPS_OUT
for (s0,s1,p0,p1,a0,a1,l0,l1,v0,v1,z0,z1,ex) in SHOTS:
    m=(t_arr>=s0)&(t_arr<s1); u=np.clip((t_arr[m]-s0)/(s1-s0),0,1); u=u*u*(3-2*u)
    P_a[m]=p0+(p1-p0)*u; TH_a[m]=a0+(a1-a0)*u; LX_a[m]=l0+(l1-l0)*u
    VY_a[m]=v0+(v1-v0)*u; Z_a[m]=z0+(z1-z0)*u; EX_a[m]=ex
TH_a=TH_a+0.20*np.sin(2*np.pi*0.085*t_arr)+0.11*np.sin(2*np.pi*0.021*t_arr+1.7)
TXm=1.3*np.sin(2*np.pi*0.065*t_arr+0.5); TYm=1.0*np.sin(2*np.pi*0.105*t_arr+2.1)
LX_a=LX_a+2.5*np.sin(2*np.pi*0.13*t_arr); VY_a=VY_a+1.8*np.sin(2*np.pi*0.09*t_arr+1.0)
PIVOT=(560.0,1150.0); PC=np.array([530.0,865.0])
def M_affine(fi):
    P,th=float(P_a[fi]),float(TH_a[fi]); z,lx,vy=float(Z_a[fi]),float(LX_a[fi]),float(VY_a[fi])
    Mp=cv2.getRotationMatrix2D(PIVOT,th,P); c=Mp[:,:2]@PC+Mp[:,2]
    Mp[0,2]+=(PC[0]-c[0])*0.5+float(TXm[fi]); Mp[1,2]+=(PC[1]-c[1])*0.5+float(TYm[fi])
    zt=1.2*z; Mc=cv2.getRotationMatrix2D((540.0,960.0),0,zt)
    Mc[0,2]+=lx; Mc[1,2]+=vy+192.0
    Mt=(np.vstack([Mc,[0,0,1]])@np.vstack([Mp,[0,0,1]]))[:2]
    return Mt
