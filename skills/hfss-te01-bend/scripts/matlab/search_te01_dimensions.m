function T=search_te01_dimensions(cfg)
% Propose dimensions of the existing linear-taper 90-degree miter bend.
% The proxy ranks phase/mode-profile agreement; it is NOT bend efficiency.
% Acceptance uses actual, converged HFSS TE01 power and bandwidth data.
if nargin<1,cfg=struct;end
defaults=struct('r1_mm',[21.5 21.75 22],'r2_mm',[16 16.125 16.25 16.5],...
 'l1_mm',20:2:28,'l_mm',[40:.25:65 125:.25:165],...
 'frequency_GHz',27.5:.1:28.5,'effective_length_offset_mm',1.27,...
 'refractive_index',sqrt(1.0006*1.0000004),'minimum_envelope_mm',0);
fields=fieldnames(defaults);
for j=1:numel(fields)
 if ~isfield(cfg,fields{j}),cfg.(fields{j})=defaults.(fields{j});end
end
folder=fileparts(mfilename('fullpath'));addpath(folder);
g=sqrt([.8677;.1296;.0027;0]);rows=[];
[~,centerIndex]=min(abs(cfg.frequency_GHz-28));
assert(abs(cfg.frequency_GHz(centerIndex)-28)<1e-8,'Include 28 GHz in the grid.');
for a=cfg.r1_mm
 for ai=cfg.r2_mm
  assert(ai<a,'The input radius must be smaller than the large guide radius.');
  for taper=cfg.l1_mm
   lengths=cfg.l_mm(cfg.l_mm+taper+2*a>=cfg.minimum_envelope_mm);
   if isempty(lengths),continue;end
   eta=zeros(numel(cfg.frequency_GHz),numel(lengths));
   for fi=1:numel(cfg.frequency_GHz)
    f=cfg.frequency_GHz(fi);
    s=te01_taper(ai,a,taper,f,4,.5,cfg.refractive_index);
    k=2*pi*f/299.792458*cfg.refractive_index;
    v=s.voltage.*sqrt(max(real(s.beta),0)/k);
    v=v.*exp(-1i*s.beta.*(lengths+a+cfg.effective_length_offset_mm));
    eta(fi,:)=abs(g'*v).^4;
   end
   score=min(eta,[],1)+.5*eta(centerIndex,:);
   % Retain both length families rather than discarding the longer solution.
   for branch=1:2
    if branch==1,indices=find(lengths<100);else,indices=find(lengths>=100);end
    if isempty(indices),continue;end
    [~,j]=max(score(indices));i=indices(j);l=lengths(i);
    rows(end+1,:)=[a,ai,l,taper,2*(a+l+taper),l+taper+2*a,branch,...
      eta(centerIndex,i),min(eta(:,i)),score(i)]; %#ok<AGROW>
   end
  end
 end
end
T=array2table(rows,'VariableNames',{'r1_mm','r2_mm','l_mm','l1_mm',...
 'total_centerline_mm','envelope_xy_mm','length_branch','proxy_center','proxy_min','score'});
T=sortrows(T,'score','descend');
writetable(T,fullfile(folder,'dimension_candidates.csv'));
disp(T(1:min(12,height(T)),:));
fprintf('Only HFSS verification can establish the requested >98%% / >96%% efficiencies.\n');
end
