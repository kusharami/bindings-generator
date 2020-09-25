#set t = $ntype.to_string($generator)
#if $ntype.is_function
	void set${pretty_name.capitalize()}(${t} value);
#else
	Q_PROPERTY(${t} ${pretty_name} READ _public_field_get_${pretty_name} WRITE _public_field_set_${pretty_name})
	${t} _public_field_get_${pretty_name}() const;
#if $ntype.is_object:
	#set $t = 'const ' + $t + '&'
#end if
	void _public_field_set_${pretty_name}(${t} value);
#end if
