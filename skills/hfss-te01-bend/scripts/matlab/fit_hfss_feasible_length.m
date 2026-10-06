function result=fit_hfss_feasible_length(sample_file,result_file,center_goal)
% Propose the shortest local length meeting a center goal from ACTUAL HFSS data.
% The prediction is a proposal only; HFSS center, bandwidth and mesh must verify it.
if nargin<3,center_goal=.981;end
T=readtable(sample_file);x=T.l_mm;y=T.center;
assert(numel(x)>=3 && numel(unique(x))>=3 && all(isfinite(x+y)));
origin=mean(x);p=polyfit(x-origin,y,2);
[observed,i]=max(y);peak=x(i);status='best_observed';
if p(1)<-1e-7
 peak=origin-p(2)/(2*p(1));peak=max(min(x),min(max(x)+1,peak));
 status='local_concave_fit';
end
q=p;q(3)=q(3)-center_goal;crossings=roots(q)+origin;
valid=crossings(abs(imag(crossings))<1e-8 & real(crossings)>=min(x) & real(crossings)<=peak);
candidate=peak;
if ~isempty(valid),candidate=min(real(valid));status='shortest_predicted_feasible_length';end
result=struct('candidate_l_mm',ceil(candidate*1000)/1000,'predicted_center',polyval(p,candidate-origin),...
 'target_center',center_goal,'peak_candidate_l_mm',round(peak,3),...
 'best_observed_center',observed,'best_observed_l_mm',x(i),'status',status,'final_verified',false);
fid=fopen(result_file,'w');assert(fid>=0);fwrite(fid,jsonencode(result,PrettyPrint=true),'char');fclose(fid);
disp(result);fprintf('Actual HFSS feedback fit; bandwidth and new mesh remain unverified.\n');
end
