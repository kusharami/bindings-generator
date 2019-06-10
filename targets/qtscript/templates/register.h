};
#for namespace_name in $current_class.namespace_list

} // end of ${namespace_name}
#end for

#set ClassName = $current_class.namespaced_class_name
#if $current_class.is_inplace_class
#if $ClassName not in $current_class.generator.ignore_metatypes
Q_DECLARE_METATYPE(${ClassName})
#end if	
#end if
#if $ClassName + '*' not in $current_class.generator.ignore_metatypes
Q_DECLARE_METATYPE(${ClassName} *)
#end if

