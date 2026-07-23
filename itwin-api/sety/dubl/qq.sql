delete from generalizedconsumers where id in (

select 
gc1.id

from generalizedconsumers gc1
join generalizedconsumers gc2 on gc1.nodeid =gc2.nodeid and gc1.id > gc2.id

);

delete from realconsumers where id in (

select 
rc1.id
from realconsumers rc1
join realconsumers rc2 on rc1.nodeid =rc2.nodeid and rc1.id > rc2.id

);
