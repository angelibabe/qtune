function scan = makePythonLineScan(cntr, range, nrepetitions, ramptime, npoints, AWGorDecaDAC)
global smdata
global tunedata
if strcmp(AWGorDecaDAC,'DecaDAC')
inst_index = sminstlookup('ATS9440Python');
config = AlazarDefaultSettings(inst_index);

%samplerate is hardcoded 100Mhz
samplerate=1e8;

masks = {};
masks{1}.type = 'Periodic Mask';
masks{1}.begin = 0;
masks{1}.end = samplerate*ramptime; % TODO: samplerate * time per point
masks{1}.period = samplerate*ramptime; % TODO: samplerate * time per point
masks{1}.channel = 'A';

operations = {};
operations{1}.type = 'DS';
operations{1}.mask = 1;

config.masks = masks;
config.operations = operations;
config.total_record_size = masks{1}.end * npoints; % npoints from loop 1, also has to be a multiple of 256;

scan.consts.setchan = 'PulseLine';
scan.consts.val = 1;

scan.saveloop = 2;
scan.disp(1).loop = 2;
scan.disp(1).channel = 1;
scan.disp(1).dim = 1;
scan.disp(2).loop = 2;
scan.disp(2).channel = 1;
scan.disp(2).dim = 2;

scan.configfn(1).fn = @smaconfigwrap;
scan.configfn(1).args = {smdata.inst(inst_index).cntrlfn [inst_index 0 99] [] [] config};
scan.configfn(2).fn = @smaconfigwrap;
scan.configfn(2).args = {smdata.inst(inst_index).cntrlfn,[inst_index 0 5]};
scan.cleanupfn(1).fn =  @smaconfigwrap;
scan.cleanupfn(1).args = {@smset, {'PulseLine'}, 1};
scan.cleanupfn(2).fn =  @smaconfigwrap;
scan.cleanupfn(2).args = {@smset, {'RFB', 'RFA'}, 0};

scan.loops(1).setchan = {'RFB', 'RFA'};
scan.loops(1).ramptime =  -1*ramptime; % TODO: adapt to parameter/samples per point
scan.loops(1).npoints = npoints; % TODO: npoints as parameter
scan.loops(1).rng = [-range range]; %[-2e-3 2e-3];%[-4e-3 0]; % TODO: parametrize as [-x 0]
scan.loops(1).trigfn.fn = @smatrigAWG;
scan.loops(1).trigfn.args = {sminstlookup('AWG5000')};
scan.loops(1).trafofn(1).fn = @(x,y,cntr)x(1)+cntr;
scan.loops(1).trafofn(1).args = {cntr};
scan.loops(1).trafofn(2).fn = @(x,y,cntr)-x(1)+cntr;
scan.loops(1).trafofn(2).args = {cntr};

scan.loops(2).setchan = 'count';
scan.loops(2).getchan = {'ATS1'};
scan.loops(2).npoints = nrepetitions; % TODO: make parameter
scan.loops(2).rng = [];
scan.loops(2).prefn(1).fn = @smaconfigwrap;
scan.loops(2).prefn(1).args = {smdata.inst(inst_index).cntrlfn,[inst_index 0 4]};
elseif strcmp(AWGorDecaDAC,'AWG')

%     tunedata.line.fastscan.loops(1).prefn(1).args{1} = awgseqind('new_line');
%     scan = tunedata.line.fastscan;
    scan = confSeqPython('new_line', 1280, nrepetitions, 'dsmask', [5 95], 'T', 1, 'operations', {'DS'});
    
else
    warning('the variable AWGorDecaDAC must be AWG or DecaDAC! You will recieve a DecaDAC scan!!!')
    scan = qtune.makePythonLineScan(center, range, gate, npoints, ramptime, numb_rep, 'DecaDAC');
end
end