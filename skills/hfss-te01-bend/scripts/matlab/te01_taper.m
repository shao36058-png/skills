function out = te01_taper(ai_mm,a_mm,L_mm,f_GHz,N,h_mm,refractive_index)
% Axisymmetric TE0n linear taper; air, PEC. All dimensions are in mm.
% Coupling reduces to thesis Eq. (2-30), m=0. Voltage/current formulation
% avoids beta=0 singularities of power-normalized coupled-wave equations.
% Stable scattering cascade includes backward and evanescent TE0n modes.
% This describes the TAPER only, not the three-dimensional miter bend.
if nargin<5,N=4;end
if nargin<6,h_mm=0.5;end
if nargin<7,refractive_index=1;end % Legacy paper checks use vacuum approximation.
roots=[3.831705970207512;7.015586669815619;10.17346813506272;13.32369193631422;16.47063005087763;19.61585851046824;22.76008438059277;25.90367208761838];
x=roots(1:N);k=2*pi*f_GHz/299.792458*refractive_index;eyeN=eye(N);zeroN=zeros(N);
% Orthonormal transverse basis J1(x_n*r/a)/(a*abs(J0(x_n))).
P=zeros(N);
for i=1:N
    for j=1:N
        if i~=j,P(i,j)=-2*x(i)*x(j)/(x(i)^2-x(j)^2)*(-1)^(i+j);end
    end
end
W=[eyeN eyeN;eyeN -eyeN];
S11=zeroN;S22=zeroN;S12=eyeN;S21=eyeN;
steps=max(1,ceil(L_mm/h_mm));dz=L_mm/steps;slope=(a_mm-ai_mm)/L_mm;
for n=1:steps
    a=ai_mm+slope*(n-.5)*dz;C=P*slope/a;
    M=[C,-1i*k*eyeN;-1i*diag(k^2-(x/a).^2)/k,C];
    T=.5*W*expm(M*dz)*W;
    B11=-(T(N+1:end,N+1:end)\T(N+1:end,1:N));
    B12=T(N+1:end,N+1:end)\eyeN;
    B21=T(1:N,1:N)+T(1:N,N+1:end)*B11;
    B22=T(1:N,N+1:end)*B12;
    U=(eyeN-B11*S22)\eyeN;V=(eyeN-S22*B11)\eyeN;
    A11=S11+S12*U*B11*S21;A12=S12*U*B12;
    A21=B21*V*S21;A22=B22+B21*V*S22*B12;
    S11=A11;S12=A12;S21=A21;S22=A22;
end
betaIn=conj(sqrt(complex(k^2-(x/ai_mm).^2)));
betaOut=conj(sqrt(complex(k^2-(x/a_mm).^2)));
Y1=diag(betaIn/k);Y2=diag(betaOut/k);
A=zeros(N,1);A(1)=1/sqrt(real(Y1(1,1)));
B=[(eyeN+Y1)-S11*(eyeN-Y1),-S12*(eyeN-Y2);-S21*(eyeN-Y1),(eyeN+Y2)-S22*(eyeN-Y2)];
rhs=[S11*(eyeN+Y1)-(eyeN-Y1);S21*(eyeN+Y1)]*A;
q=B\rhs;vr=q(1:N);vt=q(N+1:end);
powerT=abs(vt).^2.*max(0,real(betaOut/k));
powerR=abs(vr).^2.*max(0,real(betaIn/k));
out=struct('voltage',vt,'beta',betaOut,'power',powerT,'reflected_power',sum(powerR),'power_balance',sum(powerT)+sum(powerR),'phase_deg',rad2deg(angle(vt/vt(1))),'roots',x);
end
