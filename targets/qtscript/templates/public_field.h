#set t = $ntype.to_string($generator)
	Q_PROPERTY(${t} ${pretty_name} READ _public_field_get_${pretty_name} WRITE _public_field_set_${pretty_name})
	${t} _public_field_get_${pretty_name}() const;
#if $ntype.is_object or $ntype.is_function:
	#set $t = 'const ' + $t + '&'
#end if
	void _public_field_set_${pretty_name}(${t} value);
