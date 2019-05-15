int ${qtscript_class_name}::constructorArgumentCountMin() const
{
	return ${min_args};
}

int ${qtscript_class_name}::constructorArgumentCountMax() const
{
	return ${max_args};
}

#set has_base_parent = $base_parent is not None
#if $has_base_parent
	#set construct_object_type = $root_base_parent.namespaced_class_name
#else
	#set construct_object_type = $qtscript_class_name + '::NativeObjectType'
#end if
${construct_object_type} *${qtscript_class_name}::constructObject(QScriptContext *context) const
{
#if not $is_overloaded
	#set implementations = [$this_method]
#end if
	${construct_object_type} *result = nullptr;
	switch (context->argumentCount())
	{
#set cur_min_args = $min_args
#while $cur_min_args <= $max_args
		case ${cur_min_args}:
		{
	#for impl in $implementations
		#if $cur_min_args < $impl.min_args or $cur_min_args > $impl.max_args
			#continue
		#end if
		#set arg_list = []
		#if $cur_min_args > 0
			#set arg_idx = 0
			#while $arg_idx < $cur_min_args
				#set arg = $impl.arguments[$arg_idx]
				#set arg_name = $impl.argument_names[$arg_idx]
				#set arg_decl = $arg.to_string($generator)
				#set arg_name_tmp = 'tmp__' + str($arg_idx)
				#set from_qtscript = "qscriptvalue_cast<{}>(context->argument({}))".format($arg_decl, $arg_idx);
				#set arg_native = $arg.to_native({
						"generator": $generator,
						"is_const": $arg.is_const,
						"in_value": $arg_name_tmp,
						"default": $arg_name_tmp
					});
				#if $arg_native == $arg_name_tmp
				auto ${arg_name} = ${from_qtscript};
				#else
				auto ${arg_name_tmp} = ${from_qtscript};
				auto ${arg_name} = ${arg_native};
				#end if
				#set $arg_list += [$arg_name]
				#set $arg_idx += 1
			#end while
		#end if
		#set $arg_list = ", ".join($impl.get_native_call_args_with_list($arg_list));
			result = new ${class_name}(${arg_list});
		#break
	#end for
			break;
		}
	#set $cur_min_args += 1
#end while
	}
	
	if (!result)
	{
		QtScriptEngineUtils::badArgumentsException(context,
			"${namespaced_class_name} constructor");
	}
	return result;
}

