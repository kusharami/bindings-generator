#if $base_parent is not None
	Q_PROPERTY(${ntype.to_string($generator)} ${pretty_name} READ ${name} WRITE ${name})
#end if