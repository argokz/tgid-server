kod_m TableQ "$main$","externalCodes","SELECT id, name FROM externalCodes WHERE fileID=$magID$",1
uzel_m TableQ "$main$","nodes","SELECT externalNodeName FROM nodes n JOIN generalizedConsumers gc ON n.id=gc.nodeID JOIN externalCodes ec ON ec.id=n.externalCodeID WHERE n.fileID=$magID$ AND ec.name='$kod_m$' ORDER BY externalNodeName",0
