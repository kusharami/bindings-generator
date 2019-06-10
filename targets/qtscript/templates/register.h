};
#for namespace_name in $current_class.namespace_list

} // end of ${namespace_name}
#end for

#set ClassName = $current_class.namespaced_class_name
#if not $current_class.is_inplace_class and not $current_class.is_base_class and not $current_class.is_destructor_private
#set StorageType = $current_class.namespace_name + $current_class.qtscript_class_name + '::StorageType'
Q_DECLARE_METATYPE(${StorageType})
#else
#if $current_class.is_inplace_class and $ClassName not in $current_class.generator.ignore_metatypes
Q_DECLARE_METATYPE(${ClassName})
#end if
#end if
#if $ClassName + '*' not in $current_class.generator.ignore_metatypes
Q_DECLARE_METATYPE(${ClassName} *)
Q_DECLARE_METATYPE(const ${ClassName} *)
#end if

