#set cur_min_args = $min_args
#while $cur_min_args <= $max_args
	#for impl in $implementations
		#if $impl.static
			#continue
		#end if
		#if $cur_min_args < $impl.min_args or $cur_min_args > $impl.max_args
			#continue
		#end if
		#set ReturnType = $impl.ret_type.to_string($generator)
		#set arg_decl_list = ", ".join($impl.get_decl_arg_list($generator, $cur_min_args))
		#if $impl.is_property_method
	${ReturnType} ${registration_name}(${arg_decl_list});
		#else
	Q_INVOKABLE ${ReturnType} ${registration_name}(${arg_decl_list});
		#end if
		#break
	#end for
	#set $cur_min_args += 1
#end while