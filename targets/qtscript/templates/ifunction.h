#if $base_parent is not None
#set ReturnType = $ret_type.to_string($generator)
#set cur_min_args = $min_args
#while $cur_min_args <= $max_args
	#set arg_decl_list = ", ".join($this_method.get_decl_arg_list($generator, $cur_min_args))
	#if $is_property_method
	${ReturnType} ${registration_name}(${arg_decl_list});
	#else
	Q_INVOKABLE ${ReturnType} ${registration_name}(${arg_decl_list});
	#end if
	#set cur_min_args += 1
#end while
#end if