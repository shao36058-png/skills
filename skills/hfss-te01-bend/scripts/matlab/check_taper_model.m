function check_taper_model()
folder=fileparts(mfilename('fullpath'));addpath(folder);
disp(version);disp(ver);
cases=[16.27,22,25,27.94;16.25,22,20,28;16.25,22,25,28;16.25,16.25,25,28];
checks=cell(size(cases,1),1);
for i=1:size(cases,1)
    x=cases(i,:);s=te01_taper(x(1),x(2),x(3),x(4),4,.3);
    s.case=x;checks{i}=s;fprintf('CASE %s power=%s phase=%s balance=%.12g\n',mat2str(x),mat2str(s.power.',7),mat2str(s.phase_deg.',6),s.power_balance);
end
assert(abs(checks{4}.power(1)-1)<1e-8,'Uniform-guide analytic test failed');
assert(max(cellfun(@(v) abs(v.power_balance-1),checks))<1e-7,'Power conservation failed');
for i=1:numel(checks)
    s=checks{i};s.voltage_real=real(s.voltage);s.voltage_imag=imag(s.voltage);s.beta_real=real(s.beta);s.beta_imag=imag(s.beta);checks{i}=rmfield(s,{'voltage','beta'});
end
fid=fopen(fullfile(folder,'taper_checks.json'),'w');fwrite(fid,jsonencode(checks,PrettyPrint=true),'char');fclose(fid);
disp('UNIFORM_GUIDE_AND_ENERGY_CHECKS_PASSED');
end
