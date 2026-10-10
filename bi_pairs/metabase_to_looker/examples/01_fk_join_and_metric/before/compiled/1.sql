SELECT SUM(`analytics.orders`.`total`) AS `sum` FROM `analytics.orders` WHERE `analytics.orders`.`status` <> 'cancelled'
