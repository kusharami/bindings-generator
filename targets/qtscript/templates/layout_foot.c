void qtscript_register_all_${prefix}(QScriptEngine* engine)
{
	QScriptValue targetNamespace;
#set ns_count = min(len($target_ns), len($cpp_ns))
#set current_ns = None
#for cls in $sorted_classes()
	#if $cls.is_code_generated
		#set i = 0
		#if $ns_count > 0
			#while $i < $ns_count:
				#if $cls.namespace_name_no_suffix == $cpp_ns[$i]
					#break
				#end if
				#set $i += 1
			#end while
			#assert $i < $ns_count
		#end if
		#set new_current_ns = $target_ns[$i]
		#if $current_ns != $new_current_ns
			#set current_ns = $new_current_ns
	targetNamespace = QtScriptUtils::getNamespaceObject(engine, "${current_ns}");
		#end if
	${cls.namespace_name}${cls.qtscript_class_name}::Register(targetNamespace);
	#end if
#end for
}
